import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from hw_radar.acquisition.contracts import NullResolver, RawBatch, RawItem
from hw_radar.acquisition.pipeline import run_source
from hw_radar.acquisition.sources.ebay import (
    _TOKEN_CACHE,  # pyright: ignore[reportPrivateUsage]
    EbayAdapter,
)
from hw_radar.catalog.models import (
    FxRateDaily,
    Listing,
    OfferSnapshot,
    RetentionClass,
    RunStatus,
    StockStatus,
)

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

# Synthetic eBay Browse `item_summary/search` body (OQ8: not captured live — no
# real creds, no live network). Item 2 is a GBP listing shipping from GB: it
# must FX-stamp non-USD and flag is_international=True (ships-from, not currency,
# per EC-003).
SEARCH_RESULT: dict[str, object] = {
    "itemSummaries": [
        {
            "itemId": "v1|110500000001|0",
            "title": "Seagate Exos X18 18TB Recertified SAS",
            "itemWebUrl": "https://www.ebay.com/itm/110500000001",
            "price": {"value": "199.99", "currency": "USD"},
            "shippingOptions": [{"shippingCost": {"value": "0.00", "currency": "USD"}}],
            "itemLocation": {"country": "US"},
            "seller": {"username": "diskdeals_us"},
        },
        {
            "itemId": "v1|110500000002|0",
            "title": "WD Ultrastar DC HC550 16TB Recertified",
            "itemWebUrl": "https://www.ebay.co.uk/itm/110500000002",
            "price": {"value": "149.50", "currency": "GBP"},
            "shippingOptions": [{"shippingCost": {"value": "12.00", "currency": "GBP"}}],
            "itemLocation": {"country": "GB"},
            "seller": {"username": "uk_server_parts"},
        },
    ]
}

TOKEN_BODY = {
    "access_token": "SYNTH-TOKEN",
    "expires_in": 7200,
    "token_type": "Application Access Token",
}


@pytest.fixture(autouse=True)
def ebay_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Creds come from os.environ (OpenBao-injected at runtime); tests supply
    # throwaway values. _TOKEN_CACHE is process-global (keyed by API base) — a
    # token minted by one test must not leak into another (mirrors
    # test_http_guard's _ROBOTS_CACHE reset).
    monkeypatch.setenv("EBAY_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("EBAY_API_BASE", "https://api.ebay.com")
    _TOKEN_CACHE.clear()
    yield
    _TOKEN_CACHE.clear()


@pytest.fixture(scope="module")
def loop() -> Iterator[asyncio.AbstractEventLoop]:
    lo = asyncio.new_event_loop()
    asyncio.set_event_loop(lo)
    yield lo
    asyncio.set_event_loop(None)
    lo.close()


def _mock(
    *, counters: dict[str, int] | None = None, fail_first_search: bool = False
) -> httpx.MockTransport:
    calls = counters if counters is not None else {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/identity/v1/oauth2/token":
            calls["token"] = calls.get("token", 0) + 1
            return httpx.Response(200, json=TOKEN_BODY)
        if path == "/buy/browse/v1/item_summary/search":
            calls["search"] = calls.get("search", 0) + 1
            if fail_first_search and calls["search"] == 1:
                # A stale/revoked token: the search must invalidate the cache and
                # re-mint ONCE so the final RawItem is a real 200 (else
                # _classify_batch would flag the 401 as a failure).
                return httpx.Response(401, json={"errors": [{"message": "Invalid access token"}]})
            return httpx.Response(200, json=SEARCH_RESULT)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _run_ebay(loop: asyncio.AbstractEventLoop, transport: httpx.MockTransport):
    adapter = EbayAdapter(client=httpx.AsyncClient(transport=transport))
    return loop.run_until_complete(
        run_source(
            adapter,
            NullResolver(),
            retention_class=EbayAdapter.retention_class,
            expires_policy=EbayAdapter.expires_policy,
        )
    )


def test_ebay_persists_search_listings(loop: asyncio.AbstractEventLoop) -> None:
    run, _ = _run_ebay(loop, _mock())
    assert run.status == RunStatus.SUCCESS
    assert run.records_valid == 2
    listings = Listing.objects.filter(source_site__normalized_name="ebay")
    assert listings.count() == 2

    us = OfferSnapshot.objects.get(listing__source_listing_key="v1|110500000001|0")
    assert us.item_price == Decimal("199.99")
    assert us.shipping_price == Decimal("0.00")
    assert us.stock_status == StockStatus.IN_STOCK  # search returns active, buyable listings


def test_ebay_parse_maps_summary_fields() -> None:
    # seller_name / ships_from_country are ParsedListing fields (not persisted by
    # upsert_listing today) — assert the parse mapping directly.
    batch = RawBatch(
        source="ebay",
        fetched_at=datetime.now(UTC),
        items=[
            RawItem(
                url="https://api.ebay.com/buy/browse/v1/item_summary/search",
                payload_json=SEARCH_RESULT,
            )
        ],
    )
    parsed = {p.source_listing_key: p for p in EbayAdapter().parse(batch)}
    us = parsed["v1|110500000001|0"]
    assert us.seller_name == "diskdeals_us"
    assert us.ships_from_country == "US"
    assert us.shipping_price == Decimal("0.00")
    gb = parsed["v1|110500000002|0"]
    assert gb.currency == "GBP"
    assert gb.ships_from_country == "GB"
    assert gb.seller_name == "uk_server_parts"


def test_ebay_remints_token_on_401(loop: asyncio.AbstractEventLoop) -> None:
    counters: dict[str, int] = {}
    run, _ = _run_ebay(loop, _mock(counters=counters, fail_first_search=True))
    assert run.status == RunStatus.SUCCESS  # 401 recovered inside fetch(), final item is 200
    assert run.records_valid == 2
    assert counters["token"] == 2  # minted once, re-minted after the 401
    assert counters["search"] == 2  # first 401, retry 200


def test_ebay_non_usd_is_international_and_fx_stamped(loop: asyncio.AbstractEventLoop) -> None:
    # Pre-seed the GBP→USD daily rate so fx.stamp hits cache — no live Frankfurter
    # call. observed_date is the batch fetch date (UTC), which the pipeline uses
    # as the FX stamping basis.
    FxRateDaily.objects.create(
        rate_date=datetime.now(UTC).date(),
        base="GBP",
        quote="USD",
        rate=Decimal("1.270000"),
    )
    run, _ = _run_ebay(loop, _mock())
    assert run.status == RunStatus.SUCCESS

    gbp_listing = Listing.objects.get(source_listing_key="v1|110500000002|0")
    assert gbp_listing.is_international is True  # ships from GB (EC-003: origin, not currency)
    gbp_snap = OfferSnapshot.objects.get(listing=gbp_listing)
    assert gbp_snap.currency == "GBP"
    assert gbp_snap.usd_item_price is not None  # generated column: 149.50 * 1.27


def test_ebay_bounded_retention_and_ttl(loop: asyncio.AbstractEventLoop) -> None:
    run, _ = _run_ebay(loop, _mock())
    assert run.status == RunStatus.SUCCESS
    listing = Listing.objects.get(source_listing_key="v1|110500000001|0")
    assert listing.retention_class == RetentionClass.EBAY_LISTING_OBSERVATION
    assert listing.expires_at is not None  # DR-008 bounded TTL (<=6h)
    snap = OfferSnapshot.objects.get(listing=listing)
    assert snap.retention_class == RetentionClass.EBAY_LISTING_OBSERVATION
    assert snap.expires_at is not None


def test_ebay_probe_reuses_search(loop: asyncio.AbstractEventLoop) -> None:
    # HeartbeatProbe contract (migration 0011 flips heartbeat_enabled=True): the
    # Browse poll IS the heartbeat, so probe() reuses fetch()+parse() to yield one
    # reading per listing with no DB writes.
    adapter = EbayAdapter(client=httpx.AsyncClient(transport=_mock()))
    readings = loop.run_until_complete(adapter.probe())
    assert {r.source_sku for r in readings} == {"v1|110500000001|0", "v1|110500000002|0"}
    assert all(r.stock_status == StockStatus.IN_STOCK for r in readings)
    assert all(r.endpoint.endswith("/buy/browse/v1/item_summary/search") for r in readings)


def test_ebay_token_cached_across_fetches(loop: asyncio.AbstractEventLoop) -> None:
    # The token is minted once and reused from _TOKEN_CACHE (300s skew) — a second
    # fetch on the same client must NOT hit the rate-limited token endpoint again.
    counters: dict[str, int] = {}
    adapter = EbayAdapter(client=httpx.AsyncClient(transport=_mock(counters=counters)))
    loop.run_until_complete(adapter.fetch())
    loop.run_until_complete(adapter.fetch())
    assert counters["token"] == 1  # cache hit on the second fetch
    assert counters["search"] == 2


def test_ebay_parse_skips_malformed_summaries() -> None:
    # Defensive isinstance-narrowing: a non-list itemSummaries, a non-dict entry,
    # a summary without a price dict, and missing/mistyped shippingOptions /
    # itemLocation / seller must degrade to "skip" or a safe default, not raise.
    batch = RawBatch(
        source="ebay",
        fetched_at=datetime.now(UTC),
        items=[
            RawItem(url="https://api.ebay.com/a", payload_json={"itemSummaries": "oops"}),
            RawItem(
                url="https://api.ebay.com/b",
                payload_json={
                    "itemSummaries": [
                        "not-a-dict",
                        {"itemId": "no-price"},  # missing price dict
                        {"itemId": "bad-price-type", "price": "oops"},
                        {
                            "itemId": "v1|minimal|0",
                            "title": "Minimal",
                            "price": {"value": "50.00", "currency": "USD"},
                            "shippingOptions": "oops",  # non-list ⇒ shipping None
                            "itemLocation": "oops",  # non-dict ⇒ US default
                            "seller": "oops",  # non-dict ⇒ "" default
                        },
                    ]
                },
            ),
        ],
    )
    parsed = EbayAdapter().parse(batch)
    assert [p.source_listing_key for p in parsed] == ["v1|minimal|0"]
    only = parsed[0]
    assert only.shipping_price is None
    assert only.ships_from_country == "US"
    assert only.seller_name == ""


def test_ebay_token_never_logged(
    loop: asyncio.AbstractEventLoop, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("DEBUG"):
        run, _ = _run_ebay(loop, _mock())
    assert run.status == RunStatus.SUCCESS
    assert "SYNTH-TOKEN" not in caplog.text  # bearer token must never reach logs

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import pytest

from hw_radar.acquisition.contracts import NullResolver, RawBatch, RawItem
from hw_radar.acquisition.pipeline import run_source
from hw_radar.acquisition.sources.serverpartdeals import ServerPartDealsAdapter
from hw_radar.catalog.models import Listing, OfferSnapshot, RunStatus, StockStatus

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

SYNTHETIC = {  # synthetic Shopify products.json (OQ8: not captured live)
    "products": [
        {
            "title": "Seagate Exos X20 20TB Recertified",
            "handle": "exos-x20-20tb-recert",
            "variants": [
                {
                    "id": 111,
                    "sku": "ST20000NM002D-RECERT",
                    "price": "279.99",
                    "available": True,
                    "title": "Default",
                }
            ],
        },
        {
            "title": "WD Ultrastar DC HC560 20TB Recertified",
            "handle": "hc560-20tb-recert",
            "variants": [
                {
                    "id": 222,
                    "sku": "WUH722020BLE-RECERT",
                    "price": "289.99",
                    "available": False,
                    "title": "Default",
                }
            ],
        },
    ]
}


@pytest.fixture(scope="module")
def loop() -> Iterator[asyncio.AbstractEventLoop]:
    lo = asyncio.new_event_loop()
    asyncio.set_event_loop(lo)
    yield lo
    asyncio.set_event_loop(None)
    lo.close()


def _mock() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /admin\n")
        return httpx.Response(200, json=SYNTHETIC)

    return httpx.MockTransport(handler)


def test_serverpartdeals_persists_two_variants(loop: asyncio.AbstractEventLoop) -> None:
    adapter = ServerPartDealsAdapter(client=httpx.AsyncClient(transport=_mock()))
    run, _ = loop.run_until_complete(run_source(adapter, NullResolver()))
    assert run.status == RunStatus.SUCCESS
    assert run.records_valid == 2
    listings = Listing.objects.filter(source_site__normalized_name="serverpartdeals")
    assert listings.count() == 2
    oos = OfferSnapshot.objects.get(listing__source_listing_key="hc560-20tb-recert:222")
    assert oos.stock_status == StockStatus.OUT_OF_STOCK


def test_probe_returns_heartbeat_readings(loop: asyncio.AbstractEventLoop) -> None:
    # HeartbeatProbe contract (migration 0011 flips heartbeat_enabled=True for
    # this source): probe() must reuse fetch()+parse() to yield one cheap
    # reading per variant, with no DB writes.
    adapter = ServerPartDealsAdapter(client=httpx.AsyncClient(transport=_mock()))
    readings = loop.run_until_complete(adapter.probe())
    assert {r.source_sku for r in readings} == {
        "exos-x20-20tb-recert:111",
        "hc560-20tb-recert:222",
    }
    oos = next(r for r in readings if r.source_sku == "hc560-20tb-recert:222")
    assert oos.stock_status == StockStatus.OUT_OF_STOCK


def test_parse_skips_malformed_products_and_variants() -> None:
    # Defensive isinstance-narrowing branches (a top-level `products` that
    # isn't a list, a non-dict product, a product missing/mistyped
    # `variants`, or a non-dict variant) must degrade to "skip that entry",
    # not raise. Also covers required fields missing on an otherwise
    # well-formed product/variant (PR #12 review: KeyError-on-malformed-body
    # must degrade to "skip this entry", not crash the whole run).
    batch = RawBatch(
        source="serverpartdeals",
        fetched_at=datetime.now(UTC),
        items=[
            RawItem(
                url="https://serverpartdeals.com/collections/malformed/products.json",
                payload_json={"products": "oops-not-a-list"},
            ),
            RawItem(
                url="https://serverpartdeals.com/collections/x/products.json",
                payload_json={
                    "products": [
                        "not-a-product",
                        {"title": "No variants list", "handle": "no-variants", "variants": "oops"},
                        {"handle": "no-title", "variants": []},  # missing required `title`
                        {"title": "No handle", "variants": []},  # missing required `handle`
                        {
                            "title": "Good",
                            "handle": "exos-x20-20tb-recert",
                            "variants": [
                                "not-a-variant",
                                {"sku": "NO-ID", "price": "1.00"},  # missing required `id`
                                {"id": 333, "sku": "NO-PRICE"},  # missing required `price`
                                SYNTHETIC["products"][0]["variants"][0],
                            ],
                        },
                    ]
                },
            ),
        ],
    )
    adapter = ServerPartDealsAdapter()
    parsed = adapter.parse(batch)
    assert [p.source_listing_key for p in parsed] == ["exos-x20-20tb-recert:111"]

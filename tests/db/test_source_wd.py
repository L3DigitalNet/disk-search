import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import pytest

from hw_radar.acquisition.contracts import NullResolver, RawBatch, RawItem
from hw_radar.acquisition.pipeline import run_source
from hw_radar.acquisition.sources.wd import WdAdapter
from hw_radar.catalog.models import Listing, OfferSnapshot, RunStatus, StockStatus

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

# Synthetic WD OCC (SAP Commerce) bodies (OQ8: not captured live). The search
# sweep returns base product codes; each per-product response carries the
# variantOptions with the saleable/stockLevelStatus fingerprint. Product B's
# sole variant is saleable=false WHILE stockLevelStatus=inStock — the recon
# nuance that must map to OUT_OF_STOCK, not IN_STOCK.
SEARCH = {"products": [{"code": "WDBBGB0040HBK"}, {"code": "WDBBGB0080HBK"}]}

PRODUCTS = {
    "WDBBGB0040HBK": {
        "code": "WDBBGB0040HBK",
        "name": "WD My Book 4TB Recertified",
        "variantOptions": [
            {
                "code": "RWDBBGB0040HBK-NESN",
                "priceData": {"value": 79.99, "currency": "USD"},
                "stock": {"stockLevelStatus": "inStock"},
                "saleable": True,
            }
        ],
    },
    "WDBBGB0080HBK": {
        "code": "WDBBGB0080HBK",
        "name": "WD My Book 8TB Recertified",
        "variantOptions": [
            {
                "code": "RWDBBGB0080HBK-NESN",
                "priceData": {"value": 129.99, "currency": "USD"},
                "stock": {"stockLevelStatus": "inStock"},
                "saleable": False,  # saleable=false while inStock ⇒ OUT_OF_STOCK
            }
        ],
    },
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
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(404)  # no robots.txt ⇒ unrestricted (B1 guard allows)
        if path.endswith("/products/search"):
            return httpx.Response(200, json=SEARCH)
        code = path.rsplit("/", 1)[-1]
        return httpx.Response(200, json=PRODUCTS[code])

    return httpx.MockTransport(handler)


def test_wd_persists_variants_across_two_product_responses(
    loop: asyncio.AbstractEventLoop,
) -> None:
    adapter = WdAdapter(client=httpx.AsyncClient(transport=_mock()))
    run, _ = loop.run_until_complete(run_source(adapter, NullResolver()))
    assert run.status == RunStatus.SUCCESS
    assert run.records_valid == 2
    # search response + two per-product responses each land as a RawItem.
    assert run.records_fetched == 3
    listings = Listing.objects.filter(source_site__normalized_name="wd-recertified")
    assert listings.count() == 2

    in_stock = OfferSnapshot.objects.get(listing__source_listing_key="RWDBBGB0040HBK-NESN")
    assert in_stock.stock_status == StockStatus.IN_STOCK
    oos = OfferSnapshot.objects.get(listing__source_listing_key="RWDBBGB0080HBK-NESN")
    assert oos.stock_status == StockStatus.OUT_OF_STOCK  # saleable=false wins over inStock

    # B4 per-item raw association: each variant's snapshot points at the raw
    # payload of ITS OWN product response, not a shared/first one.
    assert in_stock.raw_payload is not None
    assert oos.raw_payload is not None
    assert in_stock.raw_payload.pk != oos.raw_payload.pk
    assert "WDBBGB0040HBK" in in_stock.raw_payload.endpoint
    assert "WDBBGB0080HBK" in oos.raw_payload.endpoint


def test_probe_returns_saleable_stock_fingerprint(loop: asyncio.AbstractEventLoop) -> None:
    # HeartbeatProbe contract (migration 0011 flips heartbeat_enabled=True): one
    # cheap reading per variant, no DB writes, saleable∧stockLevelStatus mapped.
    adapter = WdAdapter(client=httpx.AsyncClient(transport=_mock()))
    readings = loop.run_until_complete(adapter.probe())
    assert {r.source_sku for r in readings} == {"RWDBBGB0040HBK-NESN", "RWDBBGB0080HBK-NESN"}
    oos = next(r for r in readings if r.source_sku == "RWDBBGB0080HBK-NESN")
    assert oos.stock_status == StockStatus.OUT_OF_STOCK


def test_parse_skips_malformed_variants() -> None:
    # Defensive isinstance-narrowing: a non-list variantOptions, a non-dict
    # variant, and a variant missing priceData must degrade to "skip", not raise.
    batch = RawBatch(
        source="wd-recertified",
        fetched_at=datetime.now(UTC),
        items=[
            RawItem(
                url="https://api.westerndigital.com/wdwebservices/v2/us/products/A",
                payload_json={"name": "bad variants", "variantOptions": "oops"},
            ),
            RawItem(
                url="https://api.westerndigital.com/wdwebservices/v2/us/products/B",
                payload_json={
                    "name": "WD My Book 4TB Recertified",
                    "variantOptions": [
                        "not-a-dict",
                        {"code": "NO-PRICE"},  # missing priceData
                        PRODUCTS["WDBBGB0040HBK"]["variantOptions"][0],
                    ],
                },
            ),
        ],
    )
    parsed = WdAdapter().parse(batch)
    assert [p.source_listing_key for p in parsed] == ["RWDBBGB0040HBK-NESN"]

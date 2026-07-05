import asyncio
from datetime import date
from decimal import Decimal

import httpx
import pytest

from hw_radar.acquisition.contracts import ParsedListing
from hw_radar.acquisition.fx import MissingRateError, refresh_daily, stamp
from hw_radar.catalog.models import FxRateDaily

pytestmark = pytest.mark.django_db


def eur_listing() -> ParsedListing:
    return ParsedListing(
        source_listing_key="sku-eu",
        url="https://example.de/sku-eu",
        title="Demo 16TB (EU)",
        price=Decimal("100.00"),
        currency="EUR",
        ships_from_country="DE",
    )


def test_stamp_uses_newest_rate_on_or_before_observed_date() -> None:
    FxRateDaily.objects.create(rate_date=date(2026, 7, 1), base="EUR", rate=Decimal("1.05"))
    FxRateDaily.objects.create(rate_date=date(2026, 7, 4), base="EUR", rate=Decimal("1.08"))
    normalized = stamp(eur_listing(), observed_date=date(2026, 7, 5))
    assert normalized.fx_rate == Decimal("1.08")
    assert normalized.fx_pair == "EUR/USD"
    assert normalized.fx_rate_date == date(2026, 7, 4)
    assert normalized.is_international is True


def test_stamp_raises_when_no_rate_cached() -> None:
    with pytest.raises(MissingRateError):
        stamp(eur_listing(), observed_date=date(2026, 7, 5))


def test_stamp_rejects_stale_rate() -> None:
    # ADR-0008 is a *daily* rate; a weeks-old rate must not silently stamp.
    FxRateDaily.objects.create(rate_date=date(2026, 5, 1), base="EUR", rate=Decimal("1.02"))
    with pytest.raises(MissingRateError):
        stamp(eur_listing(), observed_date=date(2026, 7, 5))


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_refresh_daily_fetches_and_upserts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        base = request.url.params["base"]
        return httpx.Response(
            200, json={"base": base, "date": "2026-07-04", "rates": {"USD": 1.0842}}
        )

    transport = httpx.MockTransport(handler)

    async def drive() -> int:
        async with httpx.AsyncClient(transport=transport) as client:
            return await refresh_daily(("EUR", "GBP"), client=client)

    stored = asyncio.run(drive())
    assert stored == 2
    row = FxRateDaily.objects.get(base="EUR", rate_date=date(2026, 7, 4))
    assert row.rate == Decimal("1.0842")
    assert row.quote == "USD"
    # Idempotent: a second refresh updates, never duplicates.
    asyncio.run(drive())
    assert FxRateDaily.objects.filter(base="EUR").count() == 1

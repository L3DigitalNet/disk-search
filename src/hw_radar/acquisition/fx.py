"""ADR-0008 currency normalization: Frankfurter daily-rate cache + per-listing stamp.

USD listings stamp identity (rate 1, source "identity") so FR-004's "100%
of observations carry a stored rate" is auditable by query, not by absence.
The international flag follows ship-origin, not currency (EC-003).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import cast

import httpx
from asgiref.sync import sync_to_async

from hw_radar.acquisition.contracts import NormalizedListing, ParsedListing
from hw_radar.catalog.models import FxRateDaily

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"
DEFAULT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "CAD")
MAX_RATE_AGE_DAYS = 7  # a "daily" rate older than this refuses to stamp
HTTP_TIMEOUT_S = 10.0
HOME_COUNTRY = "US"


class MissingRateError(LookupError):
    """No usable cached rate for (currency, observed_date)."""


def stamp(parsed: ParsedListing, observed_date: date) -> NormalizedListing:
    is_international = parsed.ships_from_country != HOME_COUNTRY
    if parsed.currency == "USD":
        return NormalizedListing(
            **parsed.model_dump(),
            fx_rate=Decimal("1"),
            fx_pair="USD/USD",
            fx_rate_date=observed_date,
            fx_source="identity",
            is_international=is_international,
        )
    row = (
        FxRateDaily.objects.filter(base=parsed.currency, quote="USD", rate_date__lte=observed_date)
        .order_by("-rate_date")
        .first()
    )
    if row is None or row.rate_date < observed_date - timedelta(days=MAX_RATE_AGE_DAYS):
        raise MissingRateError(f"no fresh {parsed.currency}/USD rate on {observed_date}")
    return NormalizedListing(
        **parsed.model_dump(),
        fx_rate=row.rate,
        fx_pair=f"{parsed.currency}/USD",
        fx_rate_date=row.rate_date,
        fx_source=row.source,
        is_international=is_international,
    )


def _store_rate(base: str, rate_date: date, rate: Decimal) -> None:
    FxRateDaily.objects.update_or_create(
        rate_date=rate_date, base=base, quote="USD", defaults={"rate": rate}
    )


async def refresh_daily(
    currencies: tuple[str, ...] = DEFAULT_CURRENCIES, *, client: httpx.AsyncClient | None = None
) -> int:
    """Fetch base→USD for each currency; upsert the daily cache; return count stored."""
    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT_S)
    try:
        stored = 0
        for base in currencies:
            response = await active.get(
                f"{FRANKFURTER_BASE_URL}/latest", params={"base": base, "symbols": "USD"}
            )
            response.raise_for_status()
            data = cast("dict[str, object]", response.json())
            rate_date = date.fromisoformat(cast("str", data["date"]))
            rate = Decimal(str(cast("dict[str, float]", data["rates"])["USD"]))
            await sync_to_async(_store_rate)(base, rate_date, rate)
            stored += 1
        return stored
    finally:
        if owns_client:
            await active.aclose()

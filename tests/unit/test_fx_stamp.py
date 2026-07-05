from datetime import date
from decimal import Decimal

from hw_radar.acquisition.contracts import ParsedListing
from hw_radar.acquisition.fx import stamp


def usd_listing(country: str = "US") -> ParsedListing:
    return ParsedListing(
        source_listing_key="sku-1",
        url="https://example.com/sku-1",
        title="Demo 16TB",
        price=Decimal("199.99"),
        ships_from_country=country,
    )


def test_usd_listing_gets_identity_stamp_without_db() -> None:
    # FR-004 auditability: USD rows still carry a stored rate (identity).
    normalized = stamp(usd_listing(), observed_date=date(2026, 7, 5))
    assert normalized.fx_rate == Decimal("1")
    assert normalized.fx_pair == "USD/USD"
    assert normalized.fx_source == "identity"
    assert normalized.fx_rate_date == date(2026, 7, 5)
    assert normalized.is_international is False


def test_international_flag_follows_ship_origin_not_currency() -> None:
    # EC-003: a USD-priced listing shipping from abroad is still international.
    normalized = stamp(usd_listing(country="DE"), observed_date=date(2026, 7, 5))
    assert normalized.is_international is True

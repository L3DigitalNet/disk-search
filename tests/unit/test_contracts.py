from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from hw_radar.acquisition.contracts import (
    NullResolver,
    ParsedListing,
    RawBatch,
    RawItem,
)


def test_parsed_listing_coerces_and_validates() -> None:
    listing = ParsedListing(
        source_listing_key="sku-1",
        url="https://example.com/sku-1",
        title="Demo 16TB",
        price=Decimal("199.99"),
    )
    assert listing.currency == "USD"
    assert listing.ships_from_country == "US"
    assert listing.attrs == {}


def test_parsed_listing_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        ParsedListing(
            source_listing_key="sku-1",
            url="https://example.com/sku-1",
            title="Demo",
            price=Decimal("-1"),
        )


def test_raw_batch_holds_items() -> None:
    batch = RawBatch(
        source="demo",
        fetched_at=datetime(2026, 7, 5, tzinfo=UTC),
        items=[RawItem(url="https://example.com", payload_text="<html></html>")],
    )
    assert batch.items[0].http_status == 200


def test_null_resolver_is_a_no_op() -> None:
    # MS-1a stub: listings persist at grain=none; MS-1b swaps in the real resolver.
    NullResolver().resolve_listing(listing_id=123)

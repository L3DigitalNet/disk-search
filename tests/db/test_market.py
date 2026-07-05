from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection

from hw_radar.catalog.models import (
    Listing,
    OfferSnapshot,
    RawPayload,
    RetentionClass,
    SourceSite,
    SourceType,
    StockStatus,
)

T0 = datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def spd(db: None) -> SourceSite:
    return SourceSite.objects.create(
        name="ServerPartDeals",
        normalized_name="serverpartdeals",
        source_type=SourceType.SPECIALIST_RESELLER,
    )


@pytest.fixture
def listing(spd: SourceSite) -> Listing:
    return Listing.objects.create(
        source_site=spd,
        source_listing_key="spd-st16-recert",
        canonical_url="https://serverpartdeals.com/products/st16000nm001g",
        url_hash="a" * 64,
        title_raw="Seagate Exos X16 16TB recertified",
        retention_class=RetentionClass.MERCHANT_FACT,
    )


def test_offer_snapshot_is_a_hypertable(db: None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM timescaledb_information.hypertables"
            " WHERE hypertable_name = 'offer_snapshot'"
        )
        assert cursor.fetchone() is not None


def test_snapshots_append_not_duplicate(listing: Listing) -> None:
    for offset, price in ((0, Decimal("189.99")), (1, Decimal("179.99"))):
        OfferSnapshot.objects.create(
            listing=listing,
            observed_at=T0 + timedelta(hours=offset),
            item_price=price,
            stock_status=StockStatus.IN_STOCK,
            retention_class=RetentionClass.MERCHANT_FACT,
        )
    assert Listing.objects.count() == 1
    assert OfferSnapshot.objects.filter(listing=listing).count() == 2


def test_total_landed_price_is_generated(listing: Listing) -> None:
    snapshot = OfferSnapshot.objects.create(
        listing=listing,
        observed_at=T0,
        item_price=Decimal("100.00"),
        shipping_price=Decimal("12.50"),
        stock_status=StockStatus.IN_STOCK,
        retention_class=RetentionClass.MERCHANT_FACT,
    )
    snapshot.refresh_from_db()
    assert snapshot.total_landed_price == Decimal("112.50")


def test_duplicate_listing_key_rejected(spd: SourceSite, listing: Listing) -> None:
    with pytest.raises(IntegrityError):
        Listing.objects.create(
            source_site=spd,
            source_listing_key="spd-st16-recert",
            canonical_url="https://serverpartdeals.com/products/other",
            url_hash="b" * 64,
            title_raw="dup",
            retention_class=RetentionClass.MERCHANT_FACT,
        )


def test_retention_class_is_mandatory(db: None) -> None:
    with pytest.raises(IntegrityError):
        RawPayload.objects.create(
            provider="test",
            endpoint="/x",
            fetched_at=T0,
            content_hash="c" * 64,
            http_status=200,
        )


def test_indefinite_class_rejects_expiry(db: None) -> None:
    with pytest.raises(IntegrityError):
        RawPayload.objects.create(
            provider="test",
            endpoint="/x",
            fetched_at=T0,
            content_hash="d" * 64,
            http_status=200,
            retention_class=RetentionClass.MERCHANT_FACT,
            expires_at=T0 + timedelta(days=1),
        )


def test_bounded_class_requires_expiry(db: None) -> None:
    with pytest.raises(IntegrityError):
        RawPayload.objects.create(
            provider="test",
            endpoint="/x",
            fetched_at=T0,
            content_hash="e" * 64,
            http_status=200,
            retention_class=RetentionClass.AMAZON_EPHEMERAL,
        )


def test_search_observation_stores_no_provider_content(db: None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = 'public' AND table_name = 'search_observation'"
            " AND column_name IN ('result_title', 'result_snippet', 'provider_payload_json',"
            " 'response_json', 'response_text')"
        )
        assert cursor.fetchall() == []


def test_no_binary_columns_anywhere(db: None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name, column_name FROM information_schema.columns"
            " WHERE table_schema = 'public' AND data_type = 'bytea'"
        )
        assert cursor.fetchall() == []

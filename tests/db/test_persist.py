from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from hw_radar.acquisition.contracts import NormalizedListing, RawItem
from hw_radar.acquisition.persist import append_snapshot, store_raw, upsert_listing
from hw_radar.catalog.models import (
    Listing,
    OfferSnapshot,
    RetentionClass,
    SourceSite,
)

pytestmark = pytest.mark.django_db


def site() -> SourceSite:
    return SourceSite.objects.get(normalized_name="demo")  # seeded by migration 0005


def normalized(key: str = "sku-1", title: str = "Demo 16TB") -> NormalizedListing:
    return NormalizedListing(
        source_listing_key=key,
        url=f"https://demo.invalid/{key}",
        title=title,
        price=Decimal("199.99"),
        fx_rate=Decimal("1"),
        fx_pair="USD/USD",
        fx_rate_date=date(2026, 7, 5),
        fx_source="identity",
        is_international=False,
        stock_status="in_stock",
    )


def test_rerun_appends_snapshots_never_duplicates_listings() -> None:
    # DR-005 at substrate level: the MS-1 acceptance invariant.
    s = site()
    listing1, created1 = upsert_listing(s, normalized(), RetentionClass.MERCHANT_FACT)
    append_snapshot(listing1, normalized(), observed_at=timezone.now())
    listing2, created2 = upsert_listing(s, normalized(), RetentionClass.MERCHANT_FACT)
    append_snapshot(listing2, normalized(), observed_at=timezone.now())
    assert (created1, created2) == (True, False)
    assert listing1.pk == listing2.pk
    assert Listing.objects.filter(source_site=s).count() == 1
    assert OfferSnapshot.objects.filter(listing=listing1).count() == 2


def test_upsert_refreshes_mutable_fields() -> None:
    s = site()
    upsert_listing(s, normalized(), RetentionClass.MERCHANT_FACT)
    listing, _ = upsert_listing(
        s, normalized(title="Demo 16TB — price drop"), RetentionClass.MERCHANT_FACT
    )
    assert listing.title_raw == "Demo 16TB — price drop"


def test_snapshot_carries_fx_stamp_and_stock() -> None:
    s = site()
    listing, _ = upsert_listing(s, normalized(), RetentionClass.MERCHANT_FACT)
    snap = append_snapshot(listing, normalized(), observed_at=timezone.now())
    assert snap.fx_pair == "USD/USD"
    assert snap.fx_source == "identity"
    assert snap.stock_status == "in_stock"
    assert snap.retention_class == RetentionClass.MERCHANT_FACT


def test_bounded_retention_requires_expiry() -> None:
    # CR-007: the persist API must be able to carry bounded classes (eBay, MS-1d).
    from datetime import timedelta

    s = site()
    with pytest.raises(IntegrityError):  # DR-001 constraint
        upsert_listing(s, normalized(key="sku-ebay"), RetentionClass.EBAY_LISTING_OBSERVATION)
    listing, _ = upsert_listing(
        s,
        normalized(key="sku-ebay"),
        RetentionClass.EBAY_LISTING_OBSERVATION,
        expires_at=timezone.now() + timedelta(hours=6),
    )
    assert listing.expires_at is not None


def test_store_raw_hashes_content() -> None:
    item = RawItem(url="https://demo.invalid/page", payload_text="<html>x</html>")
    raw = store_raw(
        item,
        fetched_at=datetime(2026, 7, 5, tzinfo=UTC),
        retention_class=RetentionClass.MERCHANT_FACT,
    )
    assert len(raw.content_hash) == 64
    assert raw.http_status == 200

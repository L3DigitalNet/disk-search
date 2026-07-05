# pyright: reportIncompatibleVariableOverride=false
# django-types treats concrete nested Meta classes as incompatible with abstract
# base model Meta classes; Django's model metaclass handles this pattern.
# See identity.py header: future annotations keep JSONField[...] a resolvable
# string for the type-checker without subscripting the class at runtime.
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from django.db import models
from django.db.models.functions import Coalesce

from hw_radar.catalog.models.base import RetentionGoverned, TimeStamped, retention_constraints
from hw_radar.catalog.models.identity import ProductVariant


class SourceType(models.TextChoices):
    MANUFACTURER_STORE = "manufacturer_store", "Manufacturer store"
    SPECIALIST_RESELLER = "specialist_reseller", "Storage-specialist reseller"
    MARKETPLACE = "marketplace", "Marketplace"
    RETAILER = "retailer", "Retailer"
    SEARCH_PROVIDER = "search_provider", "Search provider"
    OTHER = "other", "Other"


class SourceSite(TimeStamped):
    """One marketplace/store; Appendix C.1 rows become rows here at MS-1."""

    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, unique=True)
    source_type = models.CharField(
        max_length=30, choices=SourceType.choices, default=SourceType.OTHER
    )
    region = models.CharField(max_length=10, blank=True, default="US")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "source_site"

    def __str__(self) -> str:
        return self.name


class StockStatus(models.TextChoices):
    IN_STOCK = "in_stock", "In stock"
    OUT_OF_STOCK = "out_of_stock", "Out of stock"
    PREORDER = "preorder", "Pre-order"
    UNKNOWN = "unknown", "Unknown"


class Seller(TimeStamped):
    """Marketplace-scoped merchant identity."""

    source_site = models.ForeignKey(SourceSite, on_delete=models.PROTECT, related_name="sellers")
    name = models.CharField(max_length=200)
    normalized_name = models.CharField(max_length=200)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "seller"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["source_site", "normalized_name"], name="seller_unique_per_site"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Listing(RetentionGoverned):
    """One merchant offer page at the ADR-0010 listing grain."""

    source_site = models.ForeignKey(SourceSite, on_delete=models.PROTECT, related_name="listings")
    seller = models.ForeignKey(
        Seller, on_delete=models.SET_NULL, related_name="listings", null=True, blank=True
    )
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, related_name="listings", null=True, blank=True
    )
    source_listing_key = models.CharField(max_length=255)
    canonical_url = models.URLField(max_length=1000)
    url_hash = models.CharField(max_length=64)
    title_raw = models.TextField()
    title_normalized = models.TextField(blank=True, default="")
    condition_label_raw = models.CharField(max_length=255, blank=True, default="")
    listing_fingerprint = models.CharField(max_length=64, blank=True, default="")
    is_international = models.BooleanField(default=False)
    page_metadata_json: models.JSONField[dict[str, object]] = models.JSONField(
        default=dict, blank=True
    )
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listing"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            *retention_constraints("listing"),
            models.UniqueConstraint(
                fields=["source_site", "source_listing_key"], name="listing_unique_per_site_key"
            ),
        ]


class OfferSnapshot(RetentionGoverned):
    """Time-series offer observation; converted to a TimescaleDB hypertable."""

    pk = models.CompositePrimaryKey("listing_id", "observed_at")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="snapshots")
    observed_at = models.DateTimeField()
    currency = models.CharField(max_length=3, default="USD")
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_landed_price = models.GeneratedField(
        expression=models.F("item_price")
        + Coalesce(models.F("shipping_price"), models.Value(Decimal("0")))
        + Coalesce(models.F("tax_price"), models.Value(Decimal("0"))),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
    )
    stock_status = models.CharField(
        max_length=20, choices=StockStatus.choices, default=StockStatus.UNKNOWN
    )
    quantity_available = models.PositiveIntegerField(null=True, blank=True)
    fx_rate = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    fx_pair = models.CharField(max_length=7, blank=True, default="")
    fx_rate_date = models.DateField(null=True, blank=True)
    fx_source = models.CharField(max_length=50, blank=True, default="")
    usd_item_price = models.GeneratedField(
        # NULL fx_rate propagates to NULL — never silently treat a foreign-currency
        # amount as USD (ADR-0008; USD rows carry the identity stamp fx_rate=1).
        expression=models.F("item_price") * models.F("fx_rate"),
        output_field=models.DecimalField(max_digits=14, decimal_places=4),
        db_persist=True,
    )
    extraction_method = models.CharField(max_length=50, blank=True, default="")
    confidence_score = models.FloatField(null=True, blank=True)
    attrs_json: models.JSONField[dict[str, object]] = models.JSONField(default=dict, blank=True)
    raw_payload = models.ForeignKey(
        "catalog.RawPayload",
        on_delete=models.SET_NULL,
        related_name="snapshots",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "offer_snapshot"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            *retention_constraints("offer_snapshot"),
            models.CheckConstraint(
                condition=(
                    models.Q(currency="USD")
                    | (
                        models.Q(fx_rate__isnull=False)
                        & ~models.Q(fx_pair="")
                        & models.Q(fx_rate_date__isnull=False)
                    )
                ),
                name="offer_snapshot_fx_stamped_non_usd",
            ),
        ]

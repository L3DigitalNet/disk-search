# pyright: reportIncompatibleVariableOverride=false
# django-types treats concrete nested Meta classes as incompatible with abstract
# base model Meta classes; Django's model metaclass handles this pattern.
from django.db import models

from hw_radar.catalog.models.base import TimeStamped


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

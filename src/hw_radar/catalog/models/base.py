from django.db import models


class RetentionClass(models.TextChoices):
    """DR-001 retention classes."""

    MERCHANT_FACT = "merchant_fact", "Merchant fact (indefinite)"
    EBAY_LISTING_OBSERVATION = "ebay_listing_observation", "eBay observation"
    AMAZON_EPHEMERAL = "amazon_ephemeral", "Amazon ephemeral"
    AMAZON_IDENTIFIER = "amazon_identifier", "Amazon identifier (indefinite)"
    TRANSIENT_DISCOVERY = "transient_discovery", "Search-provider discovery"
    TAVILY_EXTRACT = "tavily_extract", "Tavily-extracted fact (indefinite)"
    MANUFACTURER_REFERENCE = "manufacturer_reference", "Manufacturer reference"
    AVAILABILITY_HEARTBEAT = "availability_heartbeat", "Availability heartbeat (30d)"
    AVAILABILITY_HEARTBEAT_EVENT = "availability_heartbeat_event", "Heartbeat event (365d)"


INDEFINITE_RETENTION_CLASSES: tuple[RetentionClass, ...] = (
    RetentionClass.MERCHANT_FACT,
    RetentionClass.AMAZON_IDENTIFIER,
    RetentionClass.TAVILY_EXTRACT,
    RetentionClass.MANUFACTURER_REFERENCE,
)
BOUNDED_RETENTION_CLASSES: tuple[RetentionClass, ...] = (
    RetentionClass.EBAY_LISTING_OBSERVATION,
    RetentionClass.AMAZON_EPHEMERAL,
    RetentionClass.TRANSIENT_DISCOVERY,
    RetentionClass.AVAILABILITY_HEARTBEAT,
    RetentionClass.AVAILABILITY_HEARTBEAT_EVENT,
)


def retention_constraints(prefix: str) -> list[models.CheckConstraint]:
    """Return DR-001 constraints for concrete evidence models."""

    return [
        models.CheckConstraint(
            condition=~models.Q(retention_class=""),
            name=f"{prefix}_retention_class_set",
        ),
        models.CheckConstraint(
            condition=(
                models.Q(
                    retention_class__in=[c.value for c in INDEFINITE_RETENTION_CLASSES],
                    expires_at__isnull=True,
                )
                | models.Q(
                    retention_class__in=[c.value for c in BOUNDED_RETENTION_CLASSES],
                    expires_at__isnull=False,
                )
            ),
            name=f"{prefix}_retention_ttl_coherent",
        ),
    ]


class RetentionGoverned(models.Model):
    """DR-001 retention governance fields."""

    retention_class = models.CharField(max_length=40, choices=RetentionClass.choices, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ResolutionGrain(models.TextChoices):
    """C.3.3 resolution grains. String values are shared verbatim with
    matching.types.Grain — the resolver maps between them by value."""

    NONE = "none", "Unresolved"
    FAMILY = "family", "Product family"
    MODEL = "model", "Product model"
    VARIANT = "variant", "Product variant"

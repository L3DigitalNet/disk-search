# pyright: reportIncompatibleVariableOverride=false
# django-types treats concrete nested Meta classes as incompatible with abstract
# base model Meta classes; Django's model metaclass handles this pattern.
from typing import ClassVar

from django.db import models

from hw_radar.catalog.models.base import RetentionGoverned, retention_constraints
from hw_radar.catalog.models.identity import DriveUnit


class RawPayload(RetentionGoverned):
    """Cold raw evidence kept re-parseable when source terms allow it."""

    provider = models.CharField(max_length=50)
    endpoint = models.CharField(max_length=255)
    fetched_at = models.DateTimeField()
    request_json: models.JSONField[dict[str, object] | None] = models.JSONField(
        null=True, blank=True
    )
    response_json: models.JSONField[dict[str, object] | None] = models.JSONField(
        null=True, blank=True
    )
    response_text = models.TextField(null=True, blank=True)
    content_hash = models.CharField(max_length=64)
    http_status = models.PositiveSmallIntegerField()
    parse_version = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        db_table = "raw_payload"
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["content_hash"], name="raw_payload_content_hash")
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [*retention_constraints("raw_payload")]


class SearchObservation(RetentionGoverned):
    """IR-006-minimal discovery evidence: discovered URL plus our query metadata only."""

    provider = models.CharField(max_length=50)
    query_text = models.TextField()
    query_params_json: models.JSONField[dict[str, object]] = models.JSONField(
        default=dict, blank=True
    )
    observed_at = models.DateTimeField()
    result_rank = models.PositiveIntegerField(null=True, blank=True)
    result_url = models.URLField(max_length=1000)
    matched_listing = models.ForeignKey(
        "catalog.Listing",
        on_delete=models.SET_NULL,
        related_name="search_observations",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "search_observation"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            *retention_constraints("search_observation")
        ]


class VerificationEvent(RetentionGoverned):
    """Warranty-lookup cache for a physical drive unit."""

    drive_unit = models.ForeignKey(
        DriveUnit, on_delete=models.CASCADE, related_name="verifications"
    )
    provider = models.CharField(max_length=50)
    checked_at = models.DateTimeField()
    result_json: models.JSONField[dict[str, object]] = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "verification_event"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            *retention_constraints("verification_event")
        ]

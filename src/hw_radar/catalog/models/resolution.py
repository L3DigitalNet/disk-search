# pyright: reportIncompatibleVariableOverride=false
# django-types treats concrete nested Meta classes as incompatible with abstract
# base model Meta classes; Django's model metaclass handles this pattern.
"""Resolution state (spec C.3.3, ADR-0019 rule 6): the append-only
listing_resolution edge table + the unknown_model backfill view's unmanaged model.

Edges are NEVER updated or deleted; re-resolution appends a new edge and points
the prior current edge's superseded_by at it. Target FKs are most-specific-only
(lower grains NULL), mirroring Listing's denormalized rule. Identity targets are
PROTECT: edges are the audit trail (DR-010) — deleting a family/model/variant
that evidence points at must be blocked, matching ProductAlias's posture."""

from __future__ import annotations

from typing import ClassVar

from django.db import models
from django.utils import timezone

from hw_radar.catalog.models.base import ResolutionGrain, TimeStamped
from hw_radar.catalog.models.identity import ProductFamily, ProductModel, ProductVariant
from hw_radar.catalog.models.market import Listing


class ResolutionMethod(models.TextChoices):
    """C.3.3 method enum; rung numbers are evidence, methods are schema."""

    SOURCE_ALIAS = "source_alias", "Rung 0 — re-observation"
    EXACT_ALIAS = "exact_alias", "Rung 1 — exact alias"
    MPN_DECODE = "mpn_decode", "Rung 2 — grammar decode"
    ATTRIBUTE_MATCH = "attribute_match", "Rung 3 — attribute match"
    MANUAL = "manual", "Rung 4 — manual"


class ListingResolution(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="resolutions")
    grain = models.CharField(
        max_length=10, choices=ResolutionGrain.choices, default=ResolutionGrain.NONE
    )
    product_family = models.ForeignKey(
        ProductFamily, on_delete=models.PROTECT, related_name="resolutions", null=True, blank=True
    )
    product_model = models.ForeignKey(
        ProductModel, on_delete=models.PROTECT, related_name="resolutions", null=True, blank=True
    )
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="resolutions", null=True, blank=True
    )
    method = models.CharField(
        max_length=20, choices=ResolutionMethod.choices, blank=True, default=""
    )
    confidence = models.FloatField(null=True, blank=True)
    matcher_version = models.CharField(max_length=20)
    evidence: models.JSONField[dict[str, object]] = models.JSONField(default=dict, blank=True)
    resolved_at = models.DateTimeField(default=timezone.now)
    # Mutable freshness stamp (MS-1b carry-forward: unchanged_miss evidence
    # freshness). Updated in place whenever the resolver re-evaluates the
    # listing and writes NO new edge — the deliberate exception, alongside
    # is_current/superseded_by, to the append-only rule. Deliberately NOT in
    # the evidence JSON: evidence describes the verdict, this describes when
    # the verdict was last reconfirmed.
    last_evaluated_at = models.DateTimeField(default=timezone.now)
    # is_current is the STATE flag (exactly one per listing, DB-enforced below);
    # superseded_by is the audit POINTER. They are split because a partial unique
    # constraint cannot be deferred in PostgreSQL and superseded_by points at the
    # NEW edge — the apply sequence is demote-old → insert-new → link-old, and the
    # uniqueness must hold at every statement (Codex CR-002).
    is_current = models.BooleanField(default=True)
    # Explicit type argument: django-types cannot infer the field's generic
    # parameter from the "self" string form (only a real Model class narrows
    # it), and silently falls back to a bare `None` field type.
    superseded_by: models.ForeignKey[ListingResolution | None] = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="supersedes", null=True, blank=True
    )

    class Meta:
        db_table = "listing_resolution"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        grain="none",
                        product_family__isnull=True,
                        product_model__isnull=True,
                        product_variant__isnull=True,
                    )
                    | models.Q(
                        grain="family",
                        product_family__isnull=False,
                        product_model__isnull=True,
                        product_variant__isnull=True,
                    )
                    | models.Q(
                        grain="model",
                        product_family__isnull=True,
                        product_model__isnull=False,
                        product_variant__isnull=True,
                    )
                    | models.Q(
                        grain="variant",
                        product_family__isnull=True,
                        product_model__isnull=True,
                        product_variant__isnull=False,
                    )
                ),
                name="listing_resolution_grain_target_coherent",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(grain="none")
                    | (~models.Q(method="") & models.Q(confidence__isnull=False))
                ),
                name="listing_resolution_accept_carries_method",
            ),
            # DR-010/C.3.3: exactly ONE current resolution per listing, enforced
            # in the database, not by query discipline (Codex CR-002).
            models.UniqueConstraint(
                fields=["listing"],
                condition=models.Q(is_current=True),
                name="listing_resolution_one_current",
            ),
            models.CheckConstraint(
                condition=models.Q(is_current=False) | models.Q(superseded_by__isnull=True),
                name="listing_resolution_current_not_superseded",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["listing", "-resolved_at"], name="listing_res_recent"),
        ]

    def __str__(self) -> str:
        return f"listing {self.listing_id} → {self.grain} ({self.method or 'unresolved'})"  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue] - django-types has no <field>_id stubs


class UnknownModelBackfill(models.Model):
    """C.3.4 backfill queue — a database VIEW (migration 0007), not a table:
    listings below model grain + the rung-2 decoded-but-unknown set, grouped by
    decoded hypothesis with occurrence counts. Read-only; the deal-signal
    ordering column arrives with scoring (MS-3), the occurrence-triggered
    discovery loop with MS-1c."""

    hypothesis_key = models.CharField(primary_key=True, max_length=300)
    mpn_hypothesis = models.CharField(max_length=200, null=True)
    vendor_hint = models.CharField(max_length=50, null=True)
    occurrences = models.BigIntegerField()
    family_grain_count = models.BigIntegerField()
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "unknown_model_backfill"


class FetchRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DONE = "done", "Done"
    DISMISSED = "dismissed", "Dismissed"


class ReferenceFetchRequest(TimeStamped):
    """C.3.4 discovery loop, made concrete: a decoded-but-unknown MPN whose
    occurrence count crossed RefdataConfig.discovery_occurrence_threshold.
    Worked manually (Django admin) in MS-1c — 'targeted reference fetch' means
    a human/agent authors the missing seed document; rows are the queue, not
    an automated fetcher."""

    hypothesis_key = models.CharField(max_length=300, unique=True)
    mpn_hypothesis = models.CharField(max_length=200)
    vendor_hint = models.CharField(max_length=50, blank=True, default="")
    occurrences_at_enqueue = models.PositiveIntegerField()
    status = models.CharField(
        max_length=10, choices=FetchRequestStatus.choices, default=FetchRequestStatus.PENDING
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "reference_fetch_request"

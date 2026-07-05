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

from hw_radar.catalog.models.base import ResolutionGrain
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
        # self.listing.pk, not the listing_id shadow attribute: django-types
        # has no stub for Django's auto-generated `<field>_id` attributes.
        return f"listing {self.listing.pk} → {self.grain} ({self.method or 'unresolved'})"

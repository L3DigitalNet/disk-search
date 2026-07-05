"""Ordered admission gate for a source run (C.2; ADR-0016's ordered-gate pattern).

Order: cheapest/most-final check first — disabled → SKIP → paused (probe-only)
→ back-off window → token buckets. The buckets are checked last so a denial
higher up never burns tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.catalog.models import LifecycleState, RunKind


class DenyReason(StrEnum):
    DISABLED = "disabled"
    SKIPPED = "skipped"
    PAUSED = "paused_pending_fix"
    BACKING_OFF = "backing_off"
    BUCKET = "bucket_exhausted"


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    reason: DenyReason | None = None


def check_admission(
    *,
    enabled: bool,
    lifecycle_state: LifecycleState,
    run_kind: RunKind,
    backoff_until: datetime | None,
    now: datetime,
    registry: BucketRegistry,
    source_key: str,
    domain: str,
    now_s: float,
) -> AdmissionDecision:
    if not enabled:
        return AdmissionDecision(False, DenyReason.DISABLED)
    if lifecycle_state is LifecycleState.SKIP:
        return AdmissionDecision(False, DenyReason.SKIPPED)
    if lifecycle_state is LifecycleState.PAUSED_PENDING_FIX and run_kind is not RunKind.PROBE:
        return AdmissionDecision(False, DenyReason.PAUSED)
    if backoff_until is not None and backoff_until > now and run_kind is not RunKind.PROBE:
        # Probes bypass the back-off window: a paused source's failure events set
        # backoff_until, and ADR-0017's daily recovery probe must still run.
        return AdmissionDecision(False, DenyReason.BACKING_OFF)
    if not registry.admit(source_key, domain, now_s):
        return AdmissionDecision(False, DenyReason.BUCKET)
    return AdmissionDecision(True)

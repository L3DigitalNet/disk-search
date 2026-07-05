from datetime import UTC, datetime, timedelta

from hw_radar.acquisition.scheduling.admission import DenyReason, check_admission
from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.catalog.models import LifecycleState, RunKind

NOW = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)


def registry() -> BucketRegistry:
    reg = BucketRegistry()
    reg.configure_source("demo", rate_per_min=60.0, burst=3, now_s=0.0)
    return reg


def admit(**overrides: object):
    kwargs: dict[str, object] = {
        "enabled": True,
        "lifecycle_state": LifecycleState.ACTIVE,
        "run_kind": RunKind.FULL,
        "backoff_until": None,
        "now": NOW,
        "registry": registry(),
        "source_key": "demo",
        "domain": "example.com",
        "now_s": 0.0,
    }
    kwargs.update(overrides)
    return check_admission(**kwargs)  # type: ignore[arg-type]


def test_admits_healthy_source() -> None:
    assert admit().admitted


def test_denies_disabled() -> None:
    decision = admit(enabled=False)
    assert (decision.admitted, decision.reason) == (False, DenyReason.DISABLED)


def test_denies_skip_even_for_probe() -> None:
    decision = admit(lifecycle_state=LifecycleState.SKIP, run_kind=RunKind.PROBE)
    assert decision.reason == DenyReason.SKIPPED


def test_paused_denies_full_but_admits_probe() -> None:
    # ADR-0017: paused_pending_fix runs only the daily recovery probe.
    assert admit(lifecycle_state=LifecycleState.PAUSED_PENDING_FIX).reason == DenyReason.PAUSED
    assert admit(lifecycle_state=LifecycleState.PAUSED_PENDING_FIX, run_kind=RunKind.PROBE).admitted


def test_denies_while_backoff_pending() -> None:
    decision = admit(backoff_until=NOW + timedelta(minutes=5))
    assert decision.reason == DenyReason.BACKING_OFF


def test_backoff_expiry_admits() -> None:
    assert admit(backoff_until=NOW - timedelta(seconds=1)).admitted


def test_probe_bypasses_backoff_window() -> None:
    # ADR-0017: the daily recovery probe runs even while backoff_until is pending.
    decision = admit(
        lifecycle_state=LifecycleState.PAUSED_PENDING_FIX,
        run_kind=RunKind.PROBE,
        backoff_until=NOW + timedelta(hours=12),
    )
    assert decision.admitted


def test_denies_on_exhausted_bucket() -> None:
    reg = BucketRegistry()
    reg.configure_source("demo", rate_per_min=60.0, burst=0, now_s=0.0)
    decision = admit(registry=reg)
    assert decision.reason == DenyReason.BUCKET

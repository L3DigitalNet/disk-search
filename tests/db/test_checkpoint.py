import pytest

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.acquisition.scheduling.checkpoint import load_buckets, save_buckets

pytestmark = pytest.mark.django_db


def test_checkpoint_round_trip_rebases_clock() -> None:
    registry = BucketRegistry()
    registry.configure_source("demo", rate_per_min=6.0, burst=3, now_s=100.0)
    registry.admit("demo", "demo.invalid", now_s=100.0)
    save_buckets(registry)

    restored = load_buckets(now_s=5.0)  # fresh process: monotonic clock restarted
    bucket = restored.source_buckets["demo"]
    assert bucket.tokens == 2.0  # spent token survived the restart
    # Rebase: stale monotonic timestamps from the dead process must not grant
    # a huge refill credit in the new one.
    assert bucket.updated_at == 5.0


def test_load_without_checkpoint_returns_empty_registry() -> None:
    registry = load_buckets(now_s=0.0)
    assert registry.source_buckets == {}

"""ERR-007 crash recovery: token-bucket state checkpointed to PostgreSQL.

On load, every bucket's updated_at is REBASED to the caller's current
monotonic clock: the dead process's monotonic timestamps are meaningless in a
new process, and rebasing (no refill credit across restart) is the
conservative direction for politeness.
"""

from __future__ import annotations

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.catalog.models import SchedulerCheckpoint

BUCKETS_KEY = "bucket_registry"


def save_buckets(registry: BucketRegistry) -> None:
    SchedulerCheckpoint.objects.update_or_create(
        key=BUCKETS_KEY, defaults={"state_json": registry.to_state()}
    )


def load_buckets(*, now_s: float) -> BucketRegistry:
    row = SchedulerCheckpoint.objects.filter(key=BUCKETS_KEY).first()
    if row is None:
        return BucketRegistry()
    registry = BucketRegistry.from_state(row.state_json)
    for bucket in (*registry.source_buckets.values(), *registry.domain_buckets.values()):
        bucket.updated_at = now_s
    return registry

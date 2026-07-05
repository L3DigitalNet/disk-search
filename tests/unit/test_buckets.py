from hw_radar.acquisition.scheduling.buckets import BucketRegistry, TokenBucket


def test_bucket_starts_full_and_depletes() -> None:
    bucket = TokenBucket(capacity=3.0, refill_per_s=1.0 / 60, tokens=3.0, updated_at=0.0)
    assert bucket.acquire(now_s=0.0)
    assert bucket.acquire(now_s=0.0)
    assert bucket.acquire(now_s=0.0)
    assert not bucket.acquire(now_s=0.0)  # burst exhausted


def test_bucket_refills_over_time() -> None:
    bucket = TokenBucket(capacity=3.0, refill_per_s=1.0 / 60, tokens=0.0, updated_at=0.0)
    assert not bucket.acquire(now_s=30.0)  # only 0.5 tokens accrued
    assert bucket.acquire(now_s=90.0)  # 1.5 accrued since t=0 → spend 1


def test_bucket_never_exceeds_capacity() -> None:
    bucket = TokenBucket(capacity=2.0, refill_per_s=10.0, tokens=2.0, updated_at=0.0)
    bucket.refill(now_s=100.0)
    assert bucket.tokens == 2.0


def test_registry_requires_both_levels() -> None:
    registry = BucketRegistry()
    registry.configure_source("src-a", rate_per_min=60.0, burst=1, now_s=0.0)
    registry.configure_source("src-b", rate_per_min=60.0, burst=1, now_s=0.0)
    # Same domain: one tight domain bucket throttles both sources.
    registry.configure_domain("example.com", rate_per_min=60.0, burst=1, now_s=0.0)
    assert registry.admit("src-a", "example.com", now_s=0.0)
    # src-b has its own full source bucket, but the shared domain bucket is empty.
    assert not registry.admit("src-b", "example.com", now_s=0.0)


def test_registry_denial_consumes_no_tokens() -> None:
    registry = BucketRegistry()
    registry.configure_source("src-a", rate_per_min=60.0, burst=1, now_s=0.0)
    registry.configure_domain("example.com", rate_per_min=60.0, burst=0, now_s=0.0)
    assert not registry.admit("src-a", "example.com", now_s=0.0)
    # The failed domain check must not have burned the source token (both-or-neither).
    registry.configure_domain("example.com", rate_per_min=60.0, burst=1, now_s=0.0)
    assert registry.admit("src-a", "example.com", now_s=0.0)


def test_registry_state_round_trip() -> None:
    registry = BucketRegistry()
    registry.configure_source("src-a", rate_per_min=6.0, burst=3, now_s=10.0)
    registry.admit("src-a", "example.com", now_s=10.0)
    restored = BucketRegistry.from_state(registry.to_state())
    assert restored.to_state() == registry.to_state()

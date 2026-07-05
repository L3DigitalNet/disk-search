import asyncio
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from hw_radar.acquisition.contracts import NullResolver, ParsedListing, RawBatch, RawItem
from hw_radar.acquisition.pipeline import (
    _median_body_bytes,  # pyright: ignore[reportPrivateUsage]
    run_source,
)
from hw_radar.acquisition.scheduling.apply import RunOutcome, apply_run_outcome
from hw_radar.acquisition.scheduling.lifecycle import LifecycleEvent
from hw_radar.catalog.models import (
    LifecycleState,
    Listing,
    OfferSnapshot,
    RunFailureClass,
    RunKind,
    RunStatus,
    ScraperRun,
    SourceConfig,
    SourceSite,
)

# transaction=True: run_source writes from sync_to_async threads.
# serialized_rollback=True: TransactionTestCase truncation would otherwise delete
# the migration-0005 seed rows for every later test in the session.
pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


class FakeAdapter:
    name = "fake"
    site_key = "demo"
    run_kind = RunKind.FULL
    expects_json = True

    def __init__(self, items: list[RawItem], parsed: list[ParsedListing]) -> None:
        self._items = items
        self._parsed = parsed

    async def fetch(self) -> RawBatch:
        # A fresh timestamp per call: observed_at is now stamped from
        # batch.fetched_at, which is half of OfferSnapshot's (listing_id,
        # observed_at) composite PK — a fixed constant here would collide on
        # the rerun test below instead of exercising DR-005's append-only path.
        return RawBatch(source=self.name, fetched_at=datetime.now(UTC), items=self._items)

    def parse(self, batch: RawBatch) -> list[ParsedListing]:
        return self._parsed


def ok_item() -> RawItem:
    return RawItem(url="https://demo.invalid/a", payload_json={"sku": "a"})


def ok_parsed() -> ParsedListing:
    return ParsedListing(
        source_listing_key="sku-a",
        url="https://demo.invalid/a",
        title="Demo 8TB",
        price=Decimal("99.99"),
    )


def test_success_path_persists_and_reports() -> None:
    adapter = FakeAdapter([ok_item()], [ok_parsed()])
    run, outcome = asyncio.run(run_source(adapter, NullResolver()))
    assert run.status == RunStatus.SUCCESS
    assert outcome.event is LifecycleEvent.SUCCESS
    assert run.records_fetched == 1
    assert run.records_valid == 1
    assert run.listings_upserted == 1
    assert run.snapshots_appended == 1
    assert Listing.objects.filter(source_site__normalized_name="demo").count() == 1
    assert OfferSnapshot.objects.count() == 1


def test_rerun_is_append_only() -> None:
    adapter = FakeAdapter([ok_item()], [ok_parsed()])
    asyncio.run(run_source(adapter, NullResolver()))
    asyncio.run(run_source(adapter, NullResolver()))
    assert Listing.objects.filter(source_site__normalized_name="demo").count() == 1
    assert OfferSnapshot.objects.count() == 2
    assert ScraperRun.objects.count() == 2


def test_anti_bot_response_fails_the_run() -> None:
    blocked = RawItem(url="https://demo.invalid/a", http_status=403, content_type="text/html")
    adapter = FakeAdapter([blocked], [])
    run, outcome = asyncio.run(run_source(adapter, NullResolver()))
    assert run.status == RunStatus.FAILED
    assert run.failure_class == RunFailureClass.ANTI_BOT
    assert outcome.event is LifecycleEvent.ANTI_BOT
    assert Listing.objects.count() == 0


def test_zero_records_on_authentic_200_is_parser_rot() -> None:
    # ERR-003/EC-009: fetch looked healthy, extractor produced nothing.
    adapter = FakeAdapter([ok_item()], [])
    run, outcome = asyncio.run(run_source(adapter, NullResolver()))
    assert run.failure_class == RunFailureClass.PARSER_ROT
    assert outcome.event is LifecycleEvent.PARSER_ROT


def test_hanging_fetch_times_out_as_transient() -> None:
    # ADR-0012: hard fetch-stage timeout — a wedged adapter must not hold the job.
    class Hanging(FakeAdapter):
        async def fetch(self) -> RawBatch:
            await asyncio.sleep(3600)
            raise AssertionError("unreachable")

    run, outcome = asyncio.run(run_source(Hanging([], []), NullResolver(), fetch_timeout_s=0.05))
    assert run.status == RunStatus.FAILED
    assert run.failure_class == RunFailureClass.TRANSIENT
    assert outcome.event is LifecycleEvent.TRANSIENT_FAILURE


def test_resolver_crash_never_blocks_ingestion() -> None:
    # C.3: the listing persists; the resolver error is recorded, the run succeeds.
    class Exploding:
        def resolve_listing(self, listing_id: int) -> None:
            raise RuntimeError("resolver bug")

    adapter = FakeAdapter([ok_item()], [ok_parsed()])
    run, outcome = asyncio.run(run_source(adapter, Exploding()))
    assert run.status == RunStatus.SUCCESS
    assert outcome.event is LifecycleEvent.SUCCESS
    assert run.detail_json["resolver_errors"] == 1
    assert Listing.objects.count() == 1


def test_adapter_crash_is_classified() -> None:
    class Exploding(FakeAdapter):
        async def fetch(self) -> RawBatch:
            raise TimeoutError("socket timed out")

    run, outcome = asyncio.run(run_source(Exploding([], []), NullResolver()))
    assert run.status == RunStatus.FAILED
    assert run.failure_class == RunFailureClass.TRANSIENT
    assert outcome.event is LifecycleEvent.TRANSIENT_FAILURE


def test_apply_success_ramps_and_clears_backoff() -> None:
    config = SourceConfig.objects.get(source_site__normalized_name="demo")
    config.clean_polls = 3
    config.backoff_until = timezone.now() + timedelta(hours=1)
    now = timezone.now()
    apply_run_outcome(config, RunOutcome(LifecycleEvent.SUCCESS), now=now, rand=random.random)
    config.refresh_from_db()
    assert config.lifecycle_state == LifecycleState.ACTIVE
    assert config.current_interval_s == 1800  # 3600 halved, floored at 900
    assert config.clean_polls == 0
    assert config.backoff_until is None
    assert config.consecutive_failures == 0
    assert config.last_success_at is not None


def test_apply_transient_backs_off_and_resets_interval() -> None:
    config = SourceConfig.objects.get(source_site__normalized_name="demo")
    config.current_interval_s = 900
    now = timezone.now()
    apply_run_outcome(
        config, RunOutcome(LifecycleEvent.TRANSIENT_FAILURE), now=now, rand=lambda: 1.0
    )
    config.refresh_from_db()
    assert config.lifecycle_state == LifecycleState.BACKING_OFF
    assert config.consecutive_failures == 1
    assert config.clean_polls == 0
    assert config.current_interval_s == 3600  # AW-003: cadence resets to baseline
    assert config.backoff_until is not None
    assert config.backoff_until > now


def test_apply_probe_failure_is_state_neutral() -> None:
    # CR-NEW-002: a failed probe on a paused source keeps it paused, untouched —
    # no back-off window, no failure counters (the daily probe job is the cadence).
    config = SourceConfig.objects.get(source_site__normalized_name="demo")
    config.lifecycle_state = LifecycleState.PAUSED_PENDING_FIX
    config.save()
    now = timezone.now()
    apply_run_outcome(config, RunOutcome(LifecycleEvent.PROBE_FAILURE), now=now, rand=lambda: 1.0)
    config.refresh_from_db()
    assert config.lifecycle_state == LifecycleState.PAUSED_PENDING_FIX
    assert config.consecutive_failures == 0
    assert config.backoff_until is None
    assert config.last_run_at is not None


def _seed_full_run_history(
    site: SourceSite, *, runs: int, body_bytes: int, records_fetched: int
) -> None:
    now = timezone.now()
    for i in range(runs):
        ScraperRun.objects.create(
            source_site=site,
            run_kind=RunKind.FULL,
            status=RunStatus.SUCCESS,
            started_at=now - timedelta(minutes=i + 1),
            finished_at=now - timedelta(minutes=i + 1),
            records_fetched=records_fetched,
            detail_json={"body_bytes": body_bytes, "resolver_errors": 0},
        )


def _multi_item(n: int, size: int) -> list[RawItem]:
    return [
        RawItem(url=f"https://demo.invalid/{i}", payload_text="x" * size, payload_json={"sku": i})
        for i in range(n)
    ]


def _multi_parsed(n: int) -> list[ParsedListing]:
    return [
        ParsedListing(
            source_listing_key=f"sku-{i}",
            url=f"https://demo.invalid/{i}",
            title=f"Demo {i}",
            price=Decimal("99.99"),
        )
        for i in range(n)
    ]


def test_median_body_bytes_uses_per_item_average_not_run_total() -> None:
    # EC-007 regression: detail_json["body_bytes"] is a run-level SUM (6 items
    # x 1000 bytes = 6000), so the median basis must recover the per-item
    # average (~1000), not the raw run total (~6000).
    site = SourceSite.objects.get(normalized_name="demo")
    _seed_full_run_history(site, runs=3, body_bytes=6000, records_fetched=6)
    assert _median_body_bytes(site) == 1000


def test_healthy_multi_item_run_is_not_misclassified_as_anti_bot() -> None:
    # EC-007 regression: prior to the fix, classify_response compared each
    # item's ~1000-byte body against a run-total median of ~6000, so every
    # healthy item looked like a <20% soft-block outlier and the run failed.
    site = SourceSite.objects.get(normalized_name="demo")
    _seed_full_run_history(site, runs=3, body_bytes=6000, records_fetched=6)
    adapter = FakeAdapter(_multi_item(6, 1000), _multi_parsed(6))
    run, outcome = asyncio.run(run_source(adapter, NullResolver()))
    assert run.status == RunStatus.SUCCESS
    assert run.failure_class == ""
    assert outcome.event is LifecycleEvent.SUCCESS


def test_apply_honors_retry_after_verbatim() -> None:
    config = SourceConfig.objects.get(source_site__normalized_name="demo")
    now = timezone.now()
    apply_run_outcome(
        config,
        RunOutcome(LifecycleEvent.TRANSIENT_FAILURE, retry_after_s=120.0),
        now=now,
        rand=lambda: 1.0,
    )
    config.refresh_from_db()
    assert config.backoff_until is not None
    assert abs((config.backoff_until - now).total_seconds() - 120.0) < 1.0

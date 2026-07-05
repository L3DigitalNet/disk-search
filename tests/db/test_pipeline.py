import asyncio
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from hw_radar.acquisition.contracts import NullResolver, ParsedListing, RawBatch, RawItem
from hw_radar.acquisition.pipeline import run_source
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
)

# transaction=True: run_source writes from sync_to_async threads.
# serialized_rollback=True: TransactionTestCase truncation would otherwise delete
# the migration-0005 seed rows for every later test in the session.
pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

FETCHED_AT = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)


class FakeAdapter:
    name = "fake"
    site_key = "demo"
    run_kind = RunKind.FULL
    expects_json = True

    def __init__(self, items: list[RawItem], parsed: list[ParsedListing]) -> None:
        self._items = items
        self._parsed = parsed

    async def fetch(self) -> RawBatch:
        return RawBatch(source=self.name, fetched_at=FETCHED_AT, items=self._items)

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

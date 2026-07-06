"""Stage runner: fetch → parse → normalize → resolve → persist, in a ScraperRun.

Stages are independently re-runnable (§8.1); a resolver failure never blocks
persistence (C.3 — the listing lands unresolved). ORM work runs through
sync_to_async because the runner lives on the poller's event loop.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
from collections.abc import Callable
from datetime import date, datetime

from asgiref.sync import sync_to_async
from django.utils import timezone
from pydantic import ValidationError

from hw_radar.acquisition import fx
from hw_radar.acquisition.classify import classify_exception, classify_response
from hw_radar.acquisition.contracts import (
    ListingResolver,
    NormalizedListing,
    ParsedListing,
    RawBatch,
    SourceAdapter,
)
from hw_radar.acquisition.persist import append_snapshot, store_raw, upsert_listing
from hw_radar.acquisition.scheduling.apply import RunOutcome
from hw_radar.acquisition.scheduling.lifecycle import LifecycleEvent
from hw_radar.catalog.models import (
    Listing,
    RawPayload,
    ResolutionGrain,
    RetentionClass,
    RunFailureClass,
    RunKind,
    RunStatus,
    ScraperRun,
    SourceSite,
)

logger = logging.getLogger(__name__)

MEDIAN_BODY_WINDOW = 10  # recent successful runs consulted for EC-007 body-size outliers
FETCH_TIMEOUT_S = (
    120.0  # ADR-0012 hard fetch-stage timeout; a hung adapter must not wedge the poller
)

_EVENT_BY_CLASS: dict[RunFailureClass, LifecycleEvent] = {
    RunFailureClass.TRANSIENT: LifecycleEvent.TRANSIENT_FAILURE,
    RunFailureClass.ANTI_BOT: LifecycleEvent.ANTI_BOT,
    RunFailureClass.PARSER_ROT: LifecycleEvent.PARSER_ROT,
    RunFailureClass.DEGRADATION: LifecycleEvent.DEGRADATION,
    RunFailureClass.UNKNOWN: LifecycleEvent.UNKNOWN_FAILURE,
}


class FetchFailure(Exception):
    def __init__(self, failure_class: RunFailureClass, message: str) -> None:
        super().__init__(message)
        self.failure_class = failure_class


def _median_body_bytes(site: SourceSite) -> int | None:
    # EC-007 invariant: detail_json["body_bytes"] is stored as a RUN-LEVEL SUM
    # of every item's body size (see run_source below), but classify_response
    # consumes median_body_bytes as a PER-ITEM comparison basis (an item is a
    # soft-block if its own body is <20% of the median item size). Divide each
    # run's total by its records_fetched to recover a per-item average before
    # taking the median, and restrict the window to FULL runs — heartbeat/probe
    # runs fetch a single item, which would otherwise inject a distorted
    # "average of 1" and skew the basis.
    rows = (
        ScraperRun.objects.filter(source_site=site, status=RunStatus.SUCCESS, run_kind=RunKind.FULL)
        .order_by("-started_at")
        .values_list("detail_json__body_bytes", "records_fetched")[:MEDIAN_BODY_WINDOW]
    )
    averages = [
        size / records for size, records in rows if isinstance(size, int) and size > 0 and records
    ]
    return int(statistics.median(averages)) if averages else None


def _classify_batch(batch: RawBatch, *, expects_json: bool, median: int | None) -> None:
    for item in batch.items:
        verdict = classify_response(
            http_status=item.http_status,
            content_type=item.content_type,
            expected_json=expects_json,
            body_text=item.payload_text or "",
            median_body_bytes=median,
        )
        if verdict is not None:
            raise FetchFailure(verdict, f"{item.url} classified {verdict}")


def _persist_all(
    site: SourceSite,
    batch: RawBatch,
    normalized: list[NormalizedListing],
    retention_class: RetentionClass,
    expires_at: datetime | None,
) -> tuple[list[int], int, int]:
    # CR-002: every RawItem is stored, not just items[0] — multi-request
    # connectors (e.g. WD's search sweep + per-product fetches) otherwise lose
    # provenance for every item but the first. raws is a LIST (not a dict keyed
    # by url) so duplicate source URLs each still get their own stored row.
    raws = [
        store_raw(
            item,
            fetched_at=batch.fetched_at,
            retention_class=retention_class,
            expires_at=expires_at,
        )
        for item in batch.items
    ]
    # url -> RawPayload for snapshot association; first raw per url wins when
    # a batch has duplicate source URLs (rare, but must not drop a stored row).
    by_url: dict[str, RawPayload] = {}
    for item, raw in zip(batch.items, raws, strict=True):
        by_url.setdefault(item.url, raw)
    # Single-item batches have no meaningful raw_url to key on (adapters may
    # leave it unset); fall back to the one raw payload that must be it.
    sole = raws[0] if len(raws) == 1 else None
    listing_ids: list[int] = []
    upserted = 0
    appended = 0
    # observed_at is the instant the offer was observed at fetch time, not
    # persistence time: it must match RawPayload.fetched_at and the FX stamping
    # basis (batch.fetched_at.date()) so stored raw payloads can be replayed
    # faithfully.
    observed_at = batch.fetched_at
    for record in normalized:
        listing, _created = upsert_listing(site, record, retention_class, expires_at=expires_at)
        # append_snapshot reads listing.expires_at (not the expires_at param
        # directly) so a snapshot's TTL always matches its listing's current
        # value, even if a future caller mutates the listing between calls.
        raw = by_url.get(record.raw_url) or sole  # per-item; fallback to the sole raw
        append_snapshot(listing, record, observed_at=observed_at, raw=raw)
        listing_ids.append(listing.pk)
        upserted += 1
        appended += 1
    return listing_ids, upserted, appended


def _grain_counts(listing_ids: list[int]) -> dict[str, int]:
    # POST-resolution tally (SA-003): read after resolver.resolve_listing has
    # run for every listing_id, so this reflects each listing's final grain
    # for the run, not its pre-resolve default. Every persisted listing has a
    # grain (default NONE), so counts always sum to records_valid.
    counts: dict[str, int] = {str(choice): 0 for choice in ResolutionGrain.values}
    grains = Listing.objects.filter(pk__in=listing_ids).values_list("resolution_grain", flat=True)
    for grain in grains:
        key = str(grain)
        counts[key] = counts.get(key, 0) + 1
    return counts


async def _normalize(
    parsed_records: list[ParsedListing], observed_date: date
) -> list[NormalizedListing]:
    normalized: list[NormalizedListing] = []
    for parsed in parsed_records:
        try:
            normalized.append(await sync_to_async(fx.stamp)(parsed, observed_date))
        except fx.MissingRateError:
            await fx.refresh_daily((parsed.currency,))
            normalized.append(await sync_to_async(fx.stamp)(parsed, observed_date))
    return normalized


async def run_source(
    adapter: SourceAdapter,
    resolver: ListingResolver,
    *,
    retention_class: RetentionClass = RetentionClass.MERCHANT_FACT,
    expires_policy: Callable[[datetime], datetime | None] | None = None,
    run_kind: RunKind | None = None,
    fetch_timeout_s: float = FETCH_TIMEOUT_S,
) -> tuple[ScraperRun, RunOutcome]:
    effective_kind = run_kind or adapter.run_kind
    site = await sync_to_async(SourceSite.objects.get)(normalized_name=adapter.site_key)
    run = await sync_to_async(ScraperRun.objects.create)(
        source_site=site, run_kind=effective_kind, started_at=timezone.now()
    )
    try:
        async with asyncio.timeout(fetch_timeout_s):
            batch = await adapter.fetch()
        median = await sync_to_async(_median_body_bytes)(site)
        _classify_batch(batch, expects_json=adapter.expects_json, median=median)
        try:
            parsed = adapter.parse(batch)
        except ValidationError as exc:
            raise FetchFailure(RunFailureClass.PARSER_ROT, f"validation failed: {exc}") from exc
        if batch.items and not parsed:
            raise FetchFailure(RunFailureClass.PARSER_ROT, "authentic fetch yielded 0 records")
        normalized = await _normalize(parsed, batch.fetched_at.date())
        # expires_policy is a callable, not a fixed datetime, so bounded TTLs
        # (e.g. eBay's DR-008 <=6h) stay relative to this batch's own fetch
        # time rather than the moment run_source happened to be called.
        expires_at = expires_policy(batch.fetched_at) if expires_policy else None
        listing_ids, upserted, appended = await sync_to_async(_persist_all)(
            site, batch, normalized, retention_class, expires_at
        )
        resolver_errors = 0
        for listing_id in listing_ids:
            try:
                await sync_to_async(resolver.resolve_listing)(listing_id)
            except Exception:  # resolver failure never blocks ingestion (C.3)
                logger.exception("resolver failed for listing %s", listing_id)
                resolver_errors += 1
        grain_counts = await sync_to_async(_grain_counts)(listing_ids)
        run.records_fetched = len(batch.items)
        run.records_valid = len(normalized)
        run.listings_upserted = upserted
        run.snapshots_appended = appended
        run.detail_json = {
            "body_bytes": sum(len(item.payload_text or "") for item in batch.items),
            "resolver_errors": resolver_errors,
            "grain_counts": grain_counts,
        }
        run.status = RunStatus.SUCCESS
        run.finished_at = timezone.now()
        await sync_to_async(run.save)()
        event = (
            LifecycleEvent.PROBE_SUCCESS
            if effective_kind is RunKind.PROBE
            else LifecycleEvent.SUCCESS
        )
        return run, RunOutcome(event)
    except FetchFailure as exc:
        return await _finalize_failure(run, exc.failure_class, str(exc), effective_kind)
    except Exception as exc:  # every crash must classify + record (NFR-001)
        return await _finalize_failure(run, classify_exception(exc), repr(exc), effective_kind)


async def _finalize_failure(
    run: ScraperRun, failure_class: RunFailureClass, message: str, run_kind: RunKind
) -> tuple[ScraperRun, RunOutcome]:
    logger.warning("run %s failed: %s (%s)", run.pk, failure_class, message)
    run.status = RunStatus.FAILED
    run.failure_class = failure_class
    run.error = message[:2000]
    run.finished_at = timezone.now()
    await sync_to_async(run.save)()
    if run_kind is RunKind.PROBE:
        # A failed recovery probe keeps the source paused (ADR-0017); PROBE_FAILURE
        # is state-neutral in apply_run_outcome (only last_run_at moves), so it
        # cannot stack a back-off window or remap to ANTI_BOT/etc.
        return run, RunOutcome(LifecycleEvent.PROBE_FAILURE)
    return run, RunOutcome(_EVENT_BY_CLASS[failure_class])

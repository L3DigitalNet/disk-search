# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# APScheduler 3.x ships no py.typed/stubs; keep these exact-rule exceptions scoped here.
"""Single systemd-supervised poller owning all acquisition scheduling (ADR-0012).

Per-source interval jobs are registered from SourceConfig rows; the admission
gate (buckets → back-off → lifecycle) runs inside each job, so a denied tick
is cheap. Auto-ramp/back-off changes to current_interval_s reschedule the
source's job in place. Django ORM calls go through sync_to_async.

`python -m hw_radar.poller` makes this module import BEFORE `__main__.py` runs
(runpy imports the parent package to locate `__main__` for any `-m package`
invocation) — so `__main__.py`'s django.setup() call happens too late to save
the `from hw_radar.catalog.models import ...` import below. Bootstrap here
too; django.setup() is idempotent (Apps.populate() no-ops once ready), and
pytest-django has already configured settings by the time tests import this
module, so this is a no-op there.
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hw_radar.settings")
import django
from django.apps import apps as _django_apps

if not _django_apps.ready:
    django.setup()

import asyncio
import logging
import random
import signal
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asgiref.sync import sync_to_async
from django.utils import timezone

from hw_radar.acquisition import deadman, fx
from hw_radar.acquisition.contracts import NullResolver
from hw_radar.acquisition.pipeline import run_source
from hw_radar.acquisition.scheduling.admission import check_admission
from hw_radar.acquisition.scheduling.apply import apply_run_outcome
from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.acquisition.scheduling.checkpoint import load_buckets, save_buckets
from hw_radar.acquisition.scrapy_support import install_asyncio_reactor
from hw_radar.acquisition.sources import ADAPTERS
from hw_radar.catalog.models import LifecycleState, RunKind, SourceConfig

if TYPE_CHECKING:
    from apscheduler.job import Job

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 60
DEADMAN_SECONDS = 60
CHECKPOINT_SECONDS = 60
FX_REFRESH_HOUR_UTC = 6
RECOVERY_PROBE_SECONDS = 86_400  # ADR-0017: daily recovery probe for paused sources


def heartbeat() -> None:
    logger.info("poller heartbeat: alive")


async def poll_source(site_key: str, registry: BucketRegistry, scheduler: AsyncIOScheduler) -> None:
    config = await sync_to_async(SourceConfig.objects.select_related("source_site").get)(
        source_site__normalized_name=site_key
    )
    decision = check_admission(
        enabled=config.enabled,
        lifecycle_state=LifecycleState(config.lifecycle_state),
        run_kind=RunKind.FULL,
        backoff_until=config.backoff_until,
        now=timezone.now(),
        registry=registry,
        source_key=site_key,
        domain=config.domain,
        now_s=time.monotonic(),
    )
    if not decision.admitted:
        logger.info("source %s not admitted: %s", site_key, decision.reason)
        return
    factory = ADAPTERS.get(site_key)
    if factory is None:
        logger.warning("source %s enabled but has no adapter registered", site_key)
        return
    _run, outcome = await run_source(factory(), NullResolver())
    interval_before = config.current_interval_s
    await sync_to_async(apply_run_outcome)(config, outcome, now=timezone.now(), rand=random.random)
    if config.current_interval_s != interval_before:
        job: Job | None = scheduler.get_job(f"poll-{site_key}")
        if job is not None:
            scheduler.reschedule_job(
                f"poll-{site_key}",
                trigger="interval",
                seconds=config.current_interval_s,
                jitter=max(1, config.current_interval_s // 10),
            )
            logger.info(
                "source %s rescheduled: %ss → %ss",
                site_key,
                interval_before,
                config.current_interval_s,
            )


async def refresh_fx_job() -> None:
    stored = await fx.refresh_daily()
    logger.info("fx refresh: %s pairs stored", stored)


async def deadman_job() -> None:
    await deadman.push()


async def checkpoint_job(registry: BucketRegistry) -> None:
    await sync_to_async(save_buckets)(registry)


async def recovery_probe_job(registry: BucketRegistry) -> None:
    """ADR-0017: paused_pending_fix sources get a daily probe; success reactivates."""
    paused = await sync_to_async(
        lambda: list(
            SourceConfig.objects.select_related("source_site").filter(
                enabled=True, lifecycle_state=LifecycleState.PAUSED_PENDING_FIX
            )
        )
    )()
    for config in paused:
        key = config.source_site.normalized_name
        factory = ADAPTERS.get(key)
        if factory is None:
            continue
        decision = check_admission(
            enabled=config.enabled,
            lifecycle_state=LifecycleState(config.lifecycle_state),
            run_kind=RunKind.PROBE,
            backoff_until=config.backoff_until,
            now=timezone.now(),
            registry=registry,
            source_key=key,
            domain=config.domain,
            now_s=time.monotonic(),
        )
        if not decision.admitted:
            logger.info("probe for %s not admitted: %s", key, decision.reason)
            continue
        _run, outcome = await run_source(factory(), NullResolver(), run_kind=RunKind.PROBE)
        await sync_to_async(apply_run_outcome)(
            config, outcome, now=timezone.now(), rand=random.random
        )
        logger.info("recovery probe for %s → %s", key, config.lifecycle_state)


def build_scheduler(registry: BucketRegistry, configs: Sequence[SourceConfig]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(job_defaults={"max_instances": 1, "coalesce": True})
    scheduler.add_job(heartbeat, "interval", seconds=HEARTBEAT_SECONDS, id="poller-heartbeat")
    scheduler.add_job(refresh_fx_job, "cron", hour=FX_REFRESH_HOUR_UTC, id="fx-refresh")
    scheduler.add_job(deadman_job, "interval", seconds=DEADMAN_SECONDS, id="deadman-push")
    scheduler.add_job(
        checkpoint_job,
        "interval",
        seconds=CHECKPOINT_SECONDS,
        id="bucket-checkpoint",
        args=[registry],
    )
    scheduler.add_job(
        recovery_probe_job,
        "interval",
        seconds=RECOVERY_PROBE_SECONDS,
        id="recovery-probes",
        args=[registry],
    )
    for config in configs:
        key = config.source_site.normalized_name
        registry.configure_source(
            key,
            rate_per_min=config.bucket_rate_per_min,
            burst=config.bucket_burst,
            now_s=time.monotonic(),
        )
        scheduler.add_job(
            poll_source,
            "interval",
            seconds=config.current_interval_s,
            jitter=max(1, config.current_interval_s // 10),
            misfire_grace_time=config.misfire_grace_s,
            id=f"poll-{key}",
            args=[key, registry, scheduler],
        )
    return scheduler


async def run(configs: Sequence[SourceConfig] | None = None, *, checkpoint: bool = True) -> None:
    """checkpoint=False + configs=[] is the unit-test mode: no ORM call on the
    startup/shutdown path itself (no bucket load/save, no config query). The
    registered service jobs (FX refresh, checkpoints, probes) do touch the DB —
    but only when they fire, which a short-lived unit run never reaches
    (tests/unit/test_poller.py drives run(configs=[], checkpoint=False))."""
    install_asyncio_reactor()  # before APScheduler starts; Scrapy shares this loop
    registry = (
        await sync_to_async(load_buckets)(now_s=time.monotonic())
        if checkpoint
        else BucketRegistry()
    )
    if configs is None:
        configs = await sync_to_async(
            lambda: list(SourceConfig.objects.select_related("source_site").filter(enabled=True))
        )()
    scheduler = build_scheduler(registry, configs)
    scheduler.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    logger.info("poller started (%s source job(s))", len(configs))
    await stop.wait()
    scheduler.shutdown(wait=False)
    if checkpoint:
        try:
            await sync_to_async(save_buckets)(registry)
        except Exception:  # shutdown must complete even if the DB is gone
            logger.warning("bucket checkpoint on shutdown failed", exc_info=True)
    logger.info("poller stopped")

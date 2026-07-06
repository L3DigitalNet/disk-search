# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false, reportUnknownArgumentType=false
# APScheduler 3.x is untyped, and the ADR-0012 job-defaults contract is only exposed on _job_defaults.
# job.trigger.timezone (cron trigger's tz) is likewise untyped, hence reportUnknownArgumentType.
import asyncio
import logging
import os
import signal
import subprocess
import sys

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.poller.service import HEARTBEAT_SECONDS, build_scheduler, heartbeat, run


def test_poller_package_init_is_import_light() -> None:
    # Regression guard for the service-extraction refactor. `python -m hw_radar.poller`
    # makes runpy import the poller PACKAGE (__init__) to locate __main__, BEFORE
    # __main__ runs django.setup(). That package import must stay ORM-free — the models
    # import now lives in poller.service, reached only after __main__ configures Django.
    # Proven in a clean subprocess with DJANGO_SETTINGS_MODULE unset: importing the
    # package must succeed and must NOT pull hw_radar.catalog.models into sys.modules.
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, hw_radar.poller\n"
            "assert 'hw_radar.catalog.models' not in sys.modules, "
            "sorted(m for m in sys.modules if m.startswith('hw_radar'))",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def empty_scheduler() -> AsyncIOScheduler:
    return build_scheduler(BucketRegistry(), configs=[])


def test_heartbeat_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="hw_radar.poller"):
        heartbeat()
    assert "heartbeat" in caplog.text


def test_scheduler_registers_heartbeat_job() -> None:
    scheduler = empty_scheduler()
    job = scheduler.get_job("poller-heartbeat")
    assert job is not None
    assert job.trigger.interval.total_seconds() == HEARTBEAT_SECONDS


def test_scheduler_job_defaults_follow_adr_0012() -> None:
    scheduler = empty_scheduler()
    assert scheduler._job_defaults["max_instances"] == 1
    assert scheduler._job_defaults["coalesce"] is True


def test_service_jobs_always_registered() -> None:
    scheduler = empty_scheduler()
    for job_id in (
        "poller-heartbeat",
        "fx-refresh",
        "deadman-push",
        "bucket-checkpoint",
        "recovery-probes",
        "refdata-refresh",
    ):
        assert scheduler.get_job(job_id) is not None, job_id


def test_run_shuts_down_cleanly_on_sigterm(caplog: pytest.LogCaptureFixture) -> None:
    # Faithful to the ADR-0012 systemd contract: systemd stops the unit with SIGTERM,
    # so run() must install the handler, break its wait loop, and shut the scheduler
    # down. Driving the real signal exercises the supervision path the unit depends on.
    async def drive() -> None:
        task = asyncio.ensure_future(run(configs=[], checkpoint=False))
        await asyncio.sleep(0.05)  # let run() install signal handlers + start the scheduler
        os.kill(os.getpid(), signal.SIGTERM)
        await asyncio.wait_for(task, timeout=2)

    with caplog.at_level(logging.INFO, logger="hw_radar.poller"):
        asyncio.run(drive())
    assert "poller started" in caplog.text
    assert "poller stopped" in caplog.text


def test_refdata_refresh_job_registered_on_utc_cron() -> None:
    scheduler = build_scheduler(BucketRegistry(), [])
    job = scheduler.get_job("refdata-refresh")
    assert job is not None
    # Codex CR-003: APScheduler cron triggers default to the SCHEDULER timezone,
    # which defaults to LOCAL time — the *_UTC constants are only honest if the
    # scheduler is pinned to UTC.
    assert str(job.trigger.timezone) == "UTC"


def test_scheduler_is_pinned_to_utc() -> None:
    scheduler = build_scheduler(BucketRegistry(), [])
    assert str(scheduler.timezone) == "UTC"
    fx = scheduler.get_job("fx-refresh")
    assert fx is not None
    assert str(fx.trigger.timezone) == "UTC"  # FX_REFRESH_HOUR_UTC now truthful

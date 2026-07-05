# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
# APScheduler 3.x is untyped, and the ADR-0012 job-defaults contract is only exposed on _job_defaults.
import asyncio
import logging
import os
import signal

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from hw_radar.acquisition.scheduling.buckets import BucketRegistry
from hw_radar.poller import HEARTBEAT_SECONDS, build_scheduler, heartbeat, run


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

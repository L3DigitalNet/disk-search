# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
# APScheduler 3.x is untyped, and the ADR-0012 job-defaults contract is only exposed on _job_defaults.
import logging

import pytest

from hw_radar.poller import HEARTBEAT_SECONDS, build_scheduler, heartbeat


def test_heartbeat_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="hw_radar.poller"):
        heartbeat()
    assert "heartbeat" in caplog.text


def test_scheduler_registers_heartbeat_job() -> None:
    scheduler = build_scheduler()
    job = scheduler.get_job("poller-heartbeat")
    assert job is not None
    assert job.trigger.interval.total_seconds() == HEARTBEAT_SECONDS


def test_scheduler_job_defaults_follow_adr_0012() -> None:
    scheduler = build_scheduler()
    assert scheduler._job_defaults["max_instances"] == 1
    assert scheduler._job_defaults["coalesce"] is True

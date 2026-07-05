# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# APScheduler 3.x ships no py.typed/stubs; keep these exact-rule exceptions scoped here.
"""MS-0 poller stub for the ADR-0012 single-process scheduler contract."""

import asyncio
import logging
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 60


def heartbeat() -> None:
    logger.info("poller heartbeat: alive, no jobs scheduled (MS-0 stub)")


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(job_defaults={"max_instances": 1, "coalesce": True})
    scheduler.add_job(heartbeat, "interval", seconds=HEARTBEAT_SECONDS, id="poller-heartbeat")
    return scheduler


async def run() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    logger.info("poller started (heartbeat every %ss)", HEARTBEAT_SECONDS)
    await stop.wait()
    scheduler.shutdown(wait=False)
    logger.info("poller stopped")

"""§18.5 dead-man's switch: push liveness to the off-box Uptime Kuma monitor.

No URL configured (dev) → silent no-op. Failures return False and log — the
watchdog alerts on ABSENCE of pushes, so this function must never raise.
The push URL is rendered by bao-agent (HW_RADAR_KUMA_PUSH_URL); never commit it.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

ENV_VAR = "HW_RADAR_KUMA_PUSH_URL"
TIMEOUT_S = 10.0


async def push(*, client: httpx.AsyncClient | None = None) -> bool:
    url = os.environ.get(ENV_VAR, "")
    if not url:
        return False
    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=TIMEOUT_S)
    try:
        response = await active.get(url)
        return response.status_code < 400
    except httpx.HTTPError as exc:
        logger.warning("dead-man push failed: %r", exc)
        return False
    finally:
        if owns_client:
            await active.aclose()

"""§12.1 failure classification (evaluated in tree order) + EC-007 soft-block signals.

transient → anti_bot → parser_rot → degradation → UNKNOWN. This module covers
the response/exception half; parser_rot is asserted by the pipeline when a 200
authentic page fails extraction, and degradation is computed from run metrics.
"""

from __future__ import annotations

import httpx

from hw_radar.catalog.models import RunFailureClass

TRANSIENT_STATUSES = frozenset({408, 500, 502, 504})
ANTI_BOT_STATUSES = frozenset({401, 403, 429, 503})
CHALLENGE_MARKERS = (
    "challenge-platform",  # Cloudflare
    "cf-chl",
    "cf_chl",
    "datadome",
    "captcha",
    "checking your browser",
)
SOFT_BLOCK_BODY_RATIO = 0.2  # EC-007 body-size outlier threshold


def classify_exception(exc: Exception) -> RunFailureClass:
    # httpx.TransportError (all transport subclasses inherit it) derives from
    # httpx.HTTPError(Exception), not OSError — an API timeout/connect failure
    # must back off as TRANSIENT, not escalate to UNKNOWN and pause the source.
    if isinstance(exc, TimeoutError | ConnectionError | OSError | httpx.TransportError):
        return RunFailureClass.TRANSIENT
    return RunFailureClass.UNKNOWN


def classify_response(
    *,
    http_status: int,
    content_type: str,
    expected_json: bool,
    body_text: str,
    median_body_bytes: int | None,
) -> RunFailureClass | None:
    """Classify a completed HTTP response; None means healthy-so-far."""
    if http_status in TRANSIENT_STATUSES:
        return RunFailureClass.TRANSIENT
    if http_status in ANTI_BOT_STATUSES:
        return RunFailureClass.ANTI_BOT
    if expected_json and "json" not in content_type:
        return RunFailureClass.ANTI_BOT
    lowered = body_text.lower()
    if any(marker in lowered for marker in CHALLENGE_MARKERS):
        return RunFailureClass.ANTI_BOT
    if (
        median_body_bytes is not None
        and median_body_bytes > 0
        and len(body_text) < median_body_bytes * SOFT_BLOCK_BODY_RATIO
    ):
        return RunFailureClass.ANTI_BOT
    if http_status >= 400:
        return RunFailureClass.UNKNOWN
    return None

"""Back-off ladder, Retry-After clamp, auto-ramp, latency-spike math (C.2, AW-002..005).

Pure functions with injected randomness. All numbers OQ9-provisional.
"""

from __future__ import annotations

from collections.abc import Callable

BACKOFF_BASE_S = 600.0  # 10 min
BACKOFF_CAP_S = 86_400.0  # 24 h
RETRY_AFTER_MIN_S = 1.0
AUTO_RAMP_CLEAN_POLLS = 4


def backoff_delay_s(consecutive_failures: int, rand: Callable[[], float]) -> float:
    """AW-003: random(0,1) x min(24 h, 10 min x 2^failures)."""
    envelope = min(BACKOFF_CAP_S, BACKOFF_BASE_S * 2**consecutive_failures)
    return rand() * envelope


def clamp_retry_after(retry_after_s: float, baseline_s: int) -> float:
    """AW-002: honor Retry-After verbatim, clamped to 1 s..baseline."""
    return min(max(retry_after_s, RETRY_AFTER_MIN_S), float(baseline_s))


def interval_after_success(current_s: int, ceiling_s: int, clean_polls: int) -> tuple[int, int]:
    """AW-004 earned auto-ramp: the Nth consecutive clean poll halves the interval.

    Returns (new_interval_s, new_clean_polls); the counter resets on ramp.
    """
    polls = clean_polls + 1
    if polls >= AUTO_RAMP_CLEAN_POLLS:
        return max(ceiling_s, current_s // 2), 0
    return current_s, polls


def interval_after_latency_spike(current_s: int, baseline_s: int) -> int:
    """AW-005: halve cadence (double the interval), never slower than baseline."""
    return min(baseline_s, current_s * 2)

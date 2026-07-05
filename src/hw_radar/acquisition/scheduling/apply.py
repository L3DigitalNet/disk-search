"""The single mutator of SourceConfig scheduling state.

Composes the pure pieces (lifecycle transition, back-off ladder, auto-ramp)
into one save. Nothing else writes these fields — keeping every scheduling
decision auditable at one code point.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from hw_radar.acquisition.scheduling.backoff import (
    backoff_delay_s,
    clamp_retry_after,
    interval_after_success,
)
from hw_radar.acquisition.scheduling.lifecycle import LifecycleEvent, transition
from hw_radar.catalog.models import LifecycleState, SourceConfig

_SUCCESS_EVENTS = frozenset({LifecycleEvent.SUCCESS, LifecycleEvent.PROBE_SUCCESS})
_FAILURE_EVENTS = frozenset(
    {
        LifecycleEvent.TRANSIENT_FAILURE,
        LifecycleEvent.ANTI_BOT,
        LifecycleEvent.PARSER_ROT,
        LifecycleEvent.UNKNOWN_FAILURE,
    }
)
# PROBE_FAILURE is deliberately NOT a failure event here: a failed daily probe on an
# already-paused source keeps it paused (the transition is a no-op) and must not
# stack back-off windows or failure counters — the probe cadence is the daily job.


@dataclass(frozen=True)
class RunOutcome:
    event: LifecycleEvent
    retry_after_s: float | None = None


def apply_run_outcome(
    config: SourceConfig,
    outcome: RunOutcome,
    *,
    now: datetime,
    rand: Callable[[], float],
) -> None:
    event = outcome.event
    new_state = transition(
        LifecycleState(config.lifecycle_state),
        event,
        consecutive_parser_rot=config.consecutive_parser_rot,
    )
    config.last_run_at = now

    if event in _SUCCESS_EVENTS:
        config.last_success_at = now
        config.consecutive_failures = 0
        config.consecutive_parser_rot = 0
        config.backoff_until = None
        config.current_interval_s, config.clean_polls = interval_after_success(
            config.current_interval_s, config.cadence_ceiling_s, config.clean_polls
        )
    elif event in _FAILURE_EVENTS:
        config.consecutive_failures += 1
        config.clean_polls = 0
        config.consecutive_parser_rot = (
            config.consecutive_parser_rot + 1 if event is LifecycleEvent.PARSER_ROT else 0
        )
        # AW-003: cadence resets to baseline; the back-off window rides on top.
        config.current_interval_s = config.cadence_baseline_s
        delay_s = (
            clamp_retry_after(outcome.retry_after_s, config.cadence_baseline_s)
            if outcome.retry_after_s is not None
            else backoff_delay_s(config.consecutive_failures, rand)
        )
        config.backoff_until = now + timedelta(seconds=delay_s)

    config.lifecycle_state = new_state
    config.save(
        update_fields=[
            "lifecycle_state",
            "consecutive_failures",
            "consecutive_parser_rot",
            "clean_polls",
            "current_interval_s",
            "backoff_until",
            "last_run_at",
            "last_success_at",
            "updated_at",
        ]
    )

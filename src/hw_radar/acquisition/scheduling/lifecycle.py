"""ADR-0017 source lifecycle as a pure transition function.

States live in catalog.models.LifecycleState (they persist on SourceConfig);
this module owns the legal transitions. Degradation is deliberately a signal,
not a transition (ERR-004). Transients never trip the breaker (ERR-001).
"""

from __future__ import annotations

from enum import StrEnum

from hw_radar.catalog.models import LifecycleState

PARSER_ROT_TRIP_THRESHOLD = 2  # consecutive parser_rot runs before pausing; tunable


class LifecycleEvent(StrEnum):
    SUCCESS = "success"
    TRANSIENT_FAILURE = "transient_failure"
    ANTI_BOT = "anti_bot"
    PARSER_ROT = "parser_rot"
    DEGRADATION = "degradation"
    UNKNOWN_FAILURE = "unknown_failure"
    PROBE_SUCCESS = "probe_success"
    PROBE_FAILURE = "probe_failure"
    MANUAL_SKIP = "manual_skip"
    MANUAL_REACTIVATE = "manual_reactivate"


def transition(
    state: LifecycleState, event: LifecycleEvent, *, consecutive_parser_rot: int
) -> LifecycleState:
    if event is LifecycleEvent.MANUAL_SKIP:
        return LifecycleState.SKIP
    if state is LifecycleState.SKIP:
        if event is LifecycleEvent.MANUAL_REACTIVATE:
            return LifecycleState.ACTIVE
        return LifecycleState.SKIP
    if event is LifecycleEvent.MANUAL_REACTIVATE:
        return LifecycleState.ACTIVE
    if state is LifecycleState.PAUSED_PENDING_FIX:
        if event is LifecycleEvent.PROBE_SUCCESS:
            return LifecycleState.ACTIVE
        return LifecycleState.PAUSED_PENDING_FIX
    match event:
        case LifecycleEvent.SUCCESS | LifecycleEvent.PROBE_SUCCESS:
            return LifecycleState.ACTIVE
        case LifecycleEvent.ANTI_BOT:
            return LifecycleState.PAUSED_PENDING_FIX
        case LifecycleEvent.PARSER_ROT:
            if consecutive_parser_rot + 1 >= PARSER_ROT_TRIP_THRESHOLD:
                return LifecycleState.PAUSED_PENDING_FIX
            return LifecycleState.BACKING_OFF
        case LifecycleEvent.TRANSIENT_FAILURE:
            return LifecycleState.BACKING_OFF
        case LifecycleEvent.UNKNOWN_FAILURE:
            # ADR-0017: UNKNOWN is the conservative fall-through — hold the source
            # for manual classification; never keep retrying it as if transient.
            return LifecycleState.PAUSED_PENDING_FIX
        case LifecycleEvent.DEGRADATION | LifecycleEvent.PROBE_FAILURE:
            return state

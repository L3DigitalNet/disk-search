import pytest

from hw_radar.acquisition.scheduling.lifecycle import (
    PARSER_ROT_TRIP_THRESHOLD,
    LifecycleEvent,
    transition,
)
from hw_radar.catalog.models import LifecycleState


def test_success_returns_to_active() -> None:
    assert (
        transition(LifecycleState.BACKING_OFF, LifecycleEvent.SUCCESS, consecutive_parser_rot=0)
        == LifecycleState.ACTIVE
    )


def test_transient_never_circuit_breaks() -> None:
    # ERR-001: transients back off but never trip the breaker.
    state = LifecycleState.ACTIVE
    for _ in range(50):
        state = transition(state, LifecycleEvent.TRANSIENT_FAILURE, consecutive_parser_rot=0)
    assert state == LifecycleState.BACKING_OFF


def test_anti_bot_trips_immediately() -> None:
    # ERR-002: circuit-break on the anti_bot verdict.
    assert (
        transition(LifecycleState.ACTIVE, LifecycleEvent.ANTI_BOT, consecutive_parser_rot=0)
        == LifecycleState.PAUSED_PENDING_FIX
    )


def test_parser_rot_trips_only_when_sustained() -> None:
    # AW-006: "sustained parser_rot" — first hit backs off, threshold-th consecutive hit trips.
    first = transition(LifecycleState.ACTIVE, LifecycleEvent.PARSER_ROT, consecutive_parser_rot=0)
    assert first == LifecycleState.BACKING_OFF
    tripped = transition(
        LifecycleState.BACKING_OFF,
        LifecycleEvent.PARSER_ROT,
        consecutive_parser_rot=PARSER_ROT_TRIP_THRESHOLD - 1,
    )
    assert tripped == LifecycleState.PAUSED_PENDING_FIX


def test_unknown_failure_quarantines_for_manual_classification() -> None:
    # ADR-0017: UNKNOWN → paused_pending_fix + operator attention, not retry-as-transient.
    assert (
        transition(LifecycleState.ACTIVE, LifecycleEvent.UNKNOWN_FAILURE, consecutive_parser_rot=0)
        == LifecycleState.PAUSED_PENDING_FIX
    )


def test_paused_recovers_only_via_probe_success() -> None:
    paused = LifecycleState.PAUSED_PENDING_FIX
    assert transition(paused, LifecycleEvent.SUCCESS, consecutive_parser_rot=0) == paused
    assert (
        transition(paused, LifecycleEvent.PROBE_SUCCESS, consecutive_parser_rot=0)
        == LifecycleState.ACTIVE
    )


def test_skip_is_terminal_except_manual_reactivate() -> None:
    skip = LifecycleState.SKIP
    for event in LifecycleEvent:
        if event is LifecycleEvent.MANUAL_REACTIVATE:
            continue
        assert transition(skip, event, consecutive_parser_rot=0) == skip
    assert (
        transition(skip, LifecycleEvent.MANUAL_REACTIVATE, consecutive_parser_rot=0)
        == LifecycleState.ACTIVE
    )


def test_degradation_is_a_signal_not_a_transition() -> None:
    # ERR-004: degradation alerts; it does not change scheduling state.
    assert (
        transition(LifecycleState.ACTIVE, LifecycleEvent.DEGRADATION, consecutive_parser_rot=0)
        == LifecycleState.ACTIVE
    )


@pytest.mark.parametrize("state", list(LifecycleState))
def test_manual_skip_wins_from_any_state(state: LifecycleState) -> None:
    assert (
        transition(state, LifecycleEvent.MANUAL_SKIP, consecutive_parser_rot=0)
        == LifecycleState.SKIP
    )

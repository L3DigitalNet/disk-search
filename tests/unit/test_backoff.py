from hw_radar.acquisition.scheduling.backoff import (
    BACKOFF_CAP_S,
    backoff_delay_s,
    clamp_retry_after,
    interval_after_latency_spike,
    interval_after_success,
)


def test_backoff_ladder_doubles_and_caps() -> None:
    # rand()=1.0 exposes the envelope: 10min * 2^failures, capped at 24h (AW-003).
    assert backoff_delay_s(1, rand=lambda: 1.0) == 1200.0
    assert backoff_delay_s(2, rand=lambda: 1.0) == 2400.0
    assert backoff_delay_s(20, rand=lambda: 1.0) == BACKOFF_CAP_S


def test_backoff_is_fully_jittered() -> None:
    # random(0,1) multiplier — rand()=0 collapses the delay (spec C.2 formula).
    assert backoff_delay_s(5, rand=lambda: 0.0) == 0.0


def test_retry_after_clamped_to_1s_and_baseline() -> None:
    assert clamp_retry_after(0.0, baseline_s=3600) == 1.0
    assert clamp_retry_after(120.0, baseline_s=3600) == 120.0
    assert clamp_retry_after(999_999.0, baseline_s=3600) == 3600.0  # AW-002 clamp


def test_auto_ramp_halves_after_four_clean_polls() -> None:
    # AW-004: 4th consecutive clean poll halves the interval, floored at ceiling.
    interval, clean = interval_after_success(3600, ceiling_s=900, clean_polls=3)
    assert (interval, clean) == (1800, 0)  # ramped, counter reset
    interval, clean = interval_after_success(3600, ceiling_s=900, clean_polls=0)
    assert (interval, clean) == (3600, 1)  # counting up, no ramp yet


def test_auto_ramp_floors_at_ceiling() -> None:
    interval, _ = interval_after_success(1000, ceiling_s=900, clean_polls=3)
    assert interval == 900


def test_latency_spike_doubles_interval_capped_at_baseline() -> None:
    # AW-005: slow down, don't stop; never drift slower than baseline.
    assert interval_after_latency_spike(900, baseline_s=3600) == 1800
    assert interval_after_latency_spike(3000, baseline_s=3600) == 3600

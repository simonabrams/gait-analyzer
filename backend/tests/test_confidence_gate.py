"""Unit tests for backend.confidence_gate. Pure function, no I/O."""
from backend.confidence_gate import (
    MIN_STRIDES_FOR_CONFIDENT,
    MIN_STRIDES_FOR_REPORT,
    evaluate,
)


def _summary(
    num_strides=20,
    num_strides_detected=None,
    cadence_avg=180.0,
    vertical_osc_avg_cm=8.0,
    knee_angle_strike_avg_deg=25.0,
    foot_strike_position_avg_cm=5.0,
    trunk_lean_avg_deg=5.0,
):
    return {
        "num_strides": num_strides,
        "num_strides_detected": num_strides_detected if num_strides_detected is not None else num_strides,
        "cadence_avg": cadence_avg,
        "vertical_osc_avg_cm": vertical_osc_avg_cm,
        "knee_angle_strike_avg_deg": knee_angle_strike_avg_deg,
        "foot_strike_position_avg_cm": foot_strike_position_avg_cm,
        "trunk_lean_avg_deg": trunk_lean_avg_deg,
    }


# ---- Stride-count gate ----
def test_below_min_strides_is_hard_fail():
    result = evaluate(_summary(num_strides=4, cadence_avg=91.4))
    assert result.hard_fail is True
    assert result.reason == "insufficient_strides"
    assert result.usable_stride_count == 4
    assert "4" in result.user_message


def test_exactly_min_strides_for_report_is_not_hard_fail():
    result = evaluate(_summary(num_strides=MIN_STRIDES_FOR_REPORT))
    assert result.hard_fail is False


def test_between_min_and_confident_is_low_confidence():
    result = evaluate(_summary(num_strides=9))
    assert result.hard_fail is False
    assert result.low_confidence is True


def test_at_min_strides_for_confident_is_not_low_confidence():
    result = evaluate(_summary(num_strides=MIN_STRIDES_FOR_CONFIDENT))
    assert result.hard_fail is False
    assert result.low_confidence is False


def test_20_strides_normal_cadence_reports_with_no_warning():
    result = evaluate(_summary(num_strides=20, cadence_avg=179.7))
    assert result.hard_fail is False
    assert result.low_confidence is False


# ---- Plausibility bounds ----
def test_implausible_cadence_is_hard_fail_even_with_enough_strides():
    """The exact real-world case from the bug report: 4 strides AND a 91.4 spm
    reading -- but this test isolates the cadence check specifically, with
    stride count well above the floor, to prove it's an independent gate."""
    result = evaluate(_summary(num_strides=20, cadence_avg=91.4))
    assert result.hard_fail is True
    assert result.reason == "implausible_cadence"
    assert result.reason_metric == "cadence_avg"


def test_cadence_at_bounds_is_not_hard_fail():
    assert evaluate(_summary(num_strides=20, cadence_avg=120.0)).hard_fail is False
    assert evaluate(_summary(num_strides=20, cadence_avg=220.0)).hard_fail is False


def test_cadence_just_outside_bounds_is_hard_fail():
    assert evaluate(_summary(num_strides=20, cadence_avg=119.9)).hard_fail is True
    assert evaluate(_summary(num_strides=20, cadence_avg=220.1)).hard_fail is True


def test_implausible_bounce_is_hard_fail():
    result = evaluate(_summary(num_strides=20, vertical_osc_avg_cm=40.0))
    assert result.hard_fail is True
    assert result.reason_metric == "vertical_osc_avg_cm"


def test_implausible_knee_drive_is_hard_fail():
    result = evaluate(_summary(num_strides=20, knee_angle_strike_avg_deg=139.7))
    assert result.hard_fail is True
    assert result.reason_metric == "knee_angle_strike_avg_deg"


def test_implausible_foot_strike_position_is_hard_fail():
    result = evaluate(_summary(num_strides=20, foot_strike_position_avg_cm=55.0))
    assert result.hard_fail is True
    assert result.reason_metric == "foot_strike_position_avg_cm"


def test_implausible_trunk_lean_is_hard_fail():
    result = evaluate(_summary(num_strides=20, trunk_lean_avg_deg=45.0))
    assert result.hard_fail is True
    assert result.reason_metric == "trunk_lean_avg_deg"


def test_missing_optional_metric_does_not_hard_fail():
    """knee/foot/trunk can legitimately be None (no visible landmarks for
    that metric in any usable stride) -- that's a data-availability gap,
    not an implausible value, and must not itself trigger a hard fail."""
    result = evaluate(_summary(num_strides=20, knee_angle_strike_avg_deg=None))
    assert result.hard_fail is False


# ---- GateResult fields used downstream (telemetry, messaging) ----
def test_gate_result_carries_detected_vs_usable_counts():
    result = evaluate(_summary(num_strides=4, num_strides_detected=6, cadence_avg=91.4))
    assert result.detected_stride_count == 6
    assert result.usable_stride_count == 4


def test_ok_result_has_no_reason_or_message():
    result = evaluate(_summary(num_strides=20))
    assert result.reason is None
    assert result.reason_metric is None
    assert result.user_message is None

"""Unit tests for backend.heuristics (evaluate_heuristics). Mock results dicts only."""
from backend.heuristics import (
    CADENCE_MIN_SPM,
    VERTICAL_OSC_MAX_CM,
    KNEE_FLEXION_MIN_DEG,
    OVERSTRIDE_CM_THRESHOLD,
    TRUNK_LEAN_MAX_DEG,
    evaluate_heuristics,
)


def _results(summary=None, strides=None):
    return {"summary": summary or {}, "strides": strides or []}


# ---- Overstriding ----
def test_overstriding_triggers_when_above_threshold():
    summary = {"foot_strike_position_avg_cm": 12.0}
    strides = [{"foot_strike_position_cm": 12.0}, {"foot_strike_position_cm": 12.0}]
    flags = evaluate_heuristics(_results(summary=summary, strides=strides))
    over = [f for f in flags if f.get("metric") == "overstriding"]
    assert len(over) == 1
    assert over[0]["value"] == 12.0
    assert over[0]["threshold"] == OVERSTRIDE_CM_THRESHOLD


def test_overstriding_does_not_trigger_when_at_or_below_threshold():
    summary = {"foot_strike_position_avg_cm": 10.0}
    strides = [{"foot_strike_position_cm": 10.0}]
    flags = evaluate_heuristics(_results(summary=summary, strides=strides))
    over = [f for f in flags if f.get("metric") == "overstriding"]
    assert len(over) == 0


def test_overstriding_does_not_trigger_when_no_foot_strike_data():
    flags = evaluate_heuristics(_results(summary={}, strides=[]))
    over = [f for f in flags if f.get("metric") == "overstriding"]
    assert len(over) == 0


# ---- Low cadence ----
def test_low_cadence_triggers_when_below_threshold():
    summary = {"cadence_avg": 160.0}
    strides = [{}]
    flags = evaluate_heuristics(_results(summary=summary, strides=strides))
    cad = [f for f in flags if f.get("metric") == "cadence"]
    assert len(cad) == 1
    assert cad[0]["value"] == 160.0
    assert cad[0]["threshold"] == CADENCE_MIN_SPM


def test_low_cadence_does_not_trigger_when_at_or_above_threshold():
    summary = {"cadence_avg": 170.0}
    flags = evaluate_heuristics(_results(summary=summary, strides=[{}]))
    cad = [f for f in flags if f.get("metric") == "cadence"]
    assert len(cad) == 0


def test_low_cadence_does_not_trigger_when_cadence_none():
    flags = evaluate_heuristics(_results(summary={}, strides=[]))
    cad = [f for f in flags if f.get("metric") == "cadence"]
    assert len(cad) == 0


# ---- Vertical oscillation ----
def test_vertical_oscillation_triggers_when_above_threshold():
    summary = {"vertical_osc_avg_cm": 12.0}
    strides = [{}]
    flags = evaluate_heuristics(_results(summary=summary, strides=strides))
    vo = [f for f in flags if f.get("metric") == "vertical_oscillation"]
    assert len(vo) == 1
    assert vo[0]["value"] == 12.0
    assert vo[0]["threshold"] == VERTICAL_OSC_MAX_CM


def test_vertical_oscillation_does_not_trigger_when_at_or_below_threshold():
    summary = {"vertical_osc_avg_cm": 10.0}
    flags = evaluate_heuristics(_results(summary=summary, strides=[{}]))
    vo = [f for f in flags if f.get("metric") == "vertical_oscillation"]
    assert len(vo) == 0


# ---- Knee flexion ----
def test_knee_flexion_triggers_when_below_threshold():
    strides = [{"knee_angle_strike_deg": 10.0}, {"knee_angle_strike_deg": 12.0}]
    flags = evaluate_heuristics(_results(summary={}, strides=strides))
    kf = [f for f in flags if f.get("metric") == "knee_flexion_at_strike"]
    assert len(kf) == 1
    assert kf[0]["value"] == 11.0
    assert kf[0]["threshold"] == KNEE_FLEXION_MIN_DEG


def test_knee_flexion_does_not_trigger_when_at_or_above_threshold():
    strides = [{"knee_angle_strike_deg": 15.0}, {"knee_angle_strike_deg": 18.0}]
    flags = evaluate_heuristics(_results(summary={}, strides=strides))
    kf = [f for f in flags if f.get("metric") == "knee_flexion_at_strike"]
    assert len(kf) == 0


def test_knee_flexion_does_not_trigger_when_no_strides_with_knee_data():
    flags = evaluate_heuristics(_results(summary={}, strides=[]))
    kf = [f for f in flags if f.get("metric") == "knee_flexion_at_strike"]
    assert len(kf) == 0


# ---- Trunk lean ----
def test_trunk_lean_triggers_when_above_threshold():
    strides = [{"trunk_lean_deg": 18.0}, {"trunk_lean_deg": 20.0}]
    flags = evaluate_heuristics(_results(summary={}, strides=strides))
    tl = [f for f in flags if f.get("metric") == "trunk_lean"]
    assert len(tl) == 1
    assert tl[0]["value"] == 19.0
    assert tl[0]["threshold"] == TRUNK_LEAN_MAX_DEG


def test_trunk_lean_does_not_trigger_when_at_or_below_threshold():
    strides = [{"trunk_lean_deg": 15.0}]
    flags = evaluate_heuristics(_results(summary={}, strides=strides))
    tl = [f for f in flags if f.get("metric") == "trunk_lean"]
    assert len(tl) == 0


def test_trunk_lean_does_not_trigger_when_no_trunk_data():
    flags = evaluate_heuristics(_results(summary={}, strides=[]))
    tl = [f for f in flags if f.get("metric") == "trunk_lean"]
    assert len(tl) == 0


# ---- Combined ----
def test_multiple_flags_can_trigger():
    summary = {"cadence_avg": 165.0, "vertical_osc_avg_cm": 11.0}
    strides = [
        {"knee_angle_strike_deg": 10.0, "foot_strike_position_cm": 12.0, "trunk_lean_deg": 16.0},
    ]
    flags = evaluate_heuristics(_results(summary=summary, strides=strides))
    assert len(flags) >= 4
    metrics = {f["metric"] for f in flags}
    assert "cadence" in metrics
    assert "vertical_oscillation" in metrics
    assert "knee_flexion_at_strike" in metrics
    assert "overstriding" in metrics
    assert "trunk_lean" in metrics


def test_no_flags_when_all_within_range():
    summary = {
        "cadence_avg": 175.0,
        "vertical_osc_avg_cm": 8.0,
    }
    strides = [
        {"knee_angle_strike_deg": 18.0, "foot_strike_position_cm": 8.0, "trunk_lean_deg": 10.0},
    ]
    flags = evaluate_heuristics(_results(summary=summary, strides=strides))
    assert len(flags) == 0

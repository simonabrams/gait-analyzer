"""Unit tests for backend.rear_confidence — pure policy functions, no I/O."""
import pytest

from backend import confidence_gate as side_gate
from backend import rear_confidence as rc


# ---- Gate: never a hard fail of the run, only a status ---------------------------
def test_gate_ok_with_plenty_of_cycles_on_both_legs():
    g = rc.evaluate_gate({"left": 14, "right": 15}, lr_consistency=0.98)
    assert g.status == "ok" and g.reason is None and g.reportable_legs == ("left", "right")


def test_gate_low_confidence_when_a_leg_is_thin_or_missing():
    thin = rc.evaluate_gate({"left": 14, "right": rc.MIN_CYCLES_FOR_REPORT}, 0.98)
    one_leg = rc.evaluate_gate({"left": 14, "right": 2}, 0.98)
    assert thin.status == "low_confidence"
    assert one_leg.status == "low_confidence" and one_leg.reportable_legs == ("left",)


def test_gate_insufficient_data_below_minimum_cycles_has_a_user_message():
    g = rc.evaluate_gate({"left": 2, "right": 4}, 0.98)
    assert g.status == "insufficient_data" and g.reason == "insufficient_cycles"
    assert "4 usable strides" in g.user_message and g.reportable_legs == ()


def test_gate_insufficient_data_when_left_right_cannot_be_trusted():
    g = rc.evaluate_gate({"left": 20, "right": 20}, lr_consistency=0.55)
    assert g.status == "insufficient_data" and g.reason == "unreliable_left_right"


def test_rear_thresholds_are_wider_than_the_side_view_gate():
    assert rc.MIN_CYCLES_FOR_REPORT <= side_gate.MIN_STRIDES_FOR_REPORT
    assert rc.MIN_CYCLES_FOR_CONFIDENT <= side_gate.MIN_STRIDES_FOR_CONFIDENT


# ---- Score / tier ---------------------------------------------------------------------
def _score(metric="hip_drop", **over):
    args = dict(usable_cycles=15, mean_visibility=1.0, fps=60.0, lr_consistency=1.0, spread_deg=0.0)
    args.update(over)
    return rc.confidence_score(metric, **args)


def test_perfect_inputs_score_one_and_each_weak_input_lowers_it():
    assert _score() == 1.0
    for weak in ({"usable_cycles": 3}, {"mean_visibility": 0.5}, {"fps": 15.0}, {"lr_consistency": 0.6}, {"spread_deg": 3.0}):
        assert _score(**weak) < 1.0


def test_spread_is_judged_against_each_metrics_own_reference():
    assert _score("hip_drop", spread_deg=4.0) < _score("pronation", spread_deg=4.0)
    assert _score("hip_drop", spread_deg=99) == _score("hip_drop", spread_deg=rc.SPREAD_REFERENCE_DEG["hip_drop"])


@pytest.mark.parametrize("metric, ceiling", list(rc.TIER_CEILING.items()))
def test_tier_never_exceeds_the_metrics_ceiling(metric, ceiling):
    assert rc.tier_for(metric, 1.0) == ceiling


def test_tier_bands():
    assert rc.tier_for("hip_drop", 0.49) == "low"
    assert rc.tier_for("hip_drop", 0.50) == "moderate"
    assert rc.tier_for("knee_valgus", 0.0) == "low"


def test_no_rear_metric_can_reach_high():
    assert all(rc.tier_for(m, 1.0) != "high" for m in rc.TIER_CEILING)


# ---- Error margin / display precision -----------------------------------------------------
def test_knee_valgus_carries_the_19_degree_margin_and_others_are_honestly_unvalidated():
    assert rc.ERROR_MARGIN_DEG["knee_valgus"] == 19.0
    assert rc.ERROR_MARGIN_DEG["hip_drop"] is None and rc.ERROR_MARGIN_DEG["pronation"] is None


def test_display_rounding_is_coarser_for_less_trustworthy_metrics():
    assert rc.display_value("hip_drop", 6.4) == 6
    assert rc.display_value("pronation", 5.2) == 6
    assert rc.display_value("knee_valgus", 7.4) == 5
    assert rc.display_value("knee_valgus", 7.6) == 10
    assert rc.display_value("knee_valgus", -7.6) == -10


# ---- Pattern bands -------------------------------------------------------------------------
@pytest.mark.parametrize("metric, value, expected", [
    ("hip_drop", 3, "typical"), ("hip_drop", 8, "elevated"), ("hip_drop", 20, "pronounced"),
    ("pronation", 0, "neutral"), ("pronation", 10, "pronation_pattern"), ("pronation", -10, "supination_pattern"),
    ("knee_valgus", 5, "neutral"), ("knee_valgus", 15, "valgus_pattern"), ("knee_valgus", -15, "varus_pattern"),
])
def test_pattern_bands(metric, value, expected):
    assert rc.pattern_for(metric, value) == expected


def test_bounds():
    assert rc.within_bounds("hip_drop", 5) and not rc.within_bounds("hip_drop", 45)
    assert rc.within_bounds("knee_valgus", -20) and not rc.within_bounds("knee_valgus", 60)


# ---- Symmetry ----------------------------------------------------------------------------------
def test_symmetry_index_zero_for_identical_and_floored_for_near_zero():
    assert rc.symmetry_index("hip_drop", 6, 6) == 0
    # Two near-zero readings differing by noise must not read as wildly asymmetric.
    assert rc.symmetry_index("hip_drop", 0.2, -0.2) == pytest.approx(100 * 0.4 / rc.SYMMETRY_FLOOR_DEG["hip_drop"])
    assert rc.symmetry_index("hip_drop", 3, 12) == pytest.approx(100 * 9 / 7.5)


def test_symmetry_bands():
    assert rc.symmetry_band(90) == "symmetric"
    assert rc.symmetry_band(70) == "mild_asymmetry"
    assert rc.symmetry_band(40) == "notable_asymmetry"


def test_every_metric_has_a_disclaimer_and_valgus_states_the_margin():
    assert set(rc.DISCLAIMERS) == {"hip_drop", "pronation", "knee_valgus", "step_width", "symmetry"}
    assert "±19°" in rc.DISCLAIMERS["knee_valgus"]
    assert all("session" in d for d in rc.DISCLAIMERS.values())

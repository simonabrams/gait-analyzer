"""Unit tests for backend.rear_metrics (compute_rear_metrics and its per-frame
signal functions). Synthetic landmarks only — no video, DB or Redis."""
import json

import pytest

from backend import rear_metrics as rm
from backend.tests.rear_fixtures import CYCLE_FRAMES, FPS, make_rear_frames, swap_left_right


def _run(**kw):
    frames = make_rear_frames(**{k: v for k, v in kw.items() if k != "fps"})
    return rm.compute_rear_metrics(frames, kw.get("fps", FPS), video_file="rear.mp4")


def _obj(rv, leg, metric):
    if metric in rm.EXPERIMENTAL_METRICS:
        return rv["legs"][leg]["experimental"][metric]
    return rv["legs"][leg][metric]


def _val(rv, leg, metric):
    obj = _obj(rv, leg, metric)
    assert obj["available"], obj
    return obj["value_pct"] if metric == "step_width" else obj["value_deg"]


# ---- Per-frame signals: sign conventions -----------------------------------
def _lm_list(**over):
    lm = [{"x": 0.5, "y": 0.5, "z": 0, "visibility": 1.0} for _ in range(33)]
    for i, (x, y) in over.items():
        lm[int(i[1:])] = {"x": x, "y": y, "z": 0, "visibility": 1.0}
    return lm


def test_pelvic_tilt_positive_when_right_hip_lower():
    lm = _lm_list(i23=(0.45, 0.50), i24=(0.55, 0.51))
    assert rm.pelvic_tilt_deg(lm) == pytest.approx(5.71, abs=0.05)  # atan(0.01 / 0.10)
    assert rm.hip_drop_from_tilt("left", 5.7) == 5.7      # left stance: right hip low = drop
    assert rm.hip_drop_from_tilt("right", 5.7) == -5.7    # right stance: same tilt = no drop


def test_knee_valgus_sign_and_size():
    # Left leg (medial = +x): knee 0.02 to the right of a straight hip-ankle line.
    valgus = _lm_list(i23=(0.45, 0.50), i25=(0.47, 0.68), i27=(0.45, 0.86))
    varus = _lm_list(i23=(0.45, 0.50), i25=(0.43, 0.68), i27=(0.45, 0.86))
    assert rm.knee_valgus_deg(valgus, "left") > 5
    assert rm.knee_valgus_deg(varus, "left") < -5
    # Mirror image on the right leg (medial = -x) gives the same sign convention.
    mirror = _lm_list(i24=(0.55, 0.50), i26=(0.53, 0.68), i28=(0.55, 0.86))
    assert rm.knee_valgus_deg(mirror, "right") == pytest.approx(rm.knee_valgus_deg(valgus, "left"), abs=1e-6)


def test_pronation_sign_heel_lateral_is_pronation():
    # Left leg: lateral = image-left, so a heel left of the ankle is pronation.
    pron = _lm_list(i27=(0.45, 0.85), i29=(0.44, 0.87))
    sup = _lm_list(i27=(0.45, 0.85), i29=(0.46, 0.87))
    assert rm.pronation_deg(pron, "left") == pytest.approx(26.57, abs=0.05)
    assert rm.pronation_deg(sup, "left") < 0
    # Right leg: lateral = image-right.
    pron_r = _lm_list(i28=(0.55, 0.85), i30=(0.56, 0.87))
    assert rm.pronation_deg(pron_r, "right") > 0


def test_signals_are_none_for_low_visibility_or_degenerate_geometry():
    lm = _lm_list(i27=(0.45, 0.85), i29=(0.44, 0.83))  # heel above ankle
    assert rm.pronation_deg(lm, "left") is None
    lm = _lm_list()
    lm[27]["visibility"] = 0.1
    assert rm.pronation_deg(lm, "left") is None
    assert rm.knee_valgus_deg(_lm_list(i23=(0.45, 0.5), i25=(0.45, 0.4), i27=(0.45, 0.8)), "left") is None


# ---- End to end on a symmetric runner --------------------------------------
def test_symmetric_runner_reports_both_legs_ok():
    rv = _run()
    assert rv["status"] == "ok"
    assert rv["legs"]["left"]["reportable"] and rv["legs"]["right"]["reportable"]
    assert rv["legs"]["left"]["cycles_usable"] >= 10
    for leg in ("left", "right"):
        assert _val(rv, leg, "hip_drop") == pytest.approx(6, abs=2)
        assert _val(rv, leg, "pronation") == pytest.approx(4, abs=3)
        assert _val(rv, leg, "knee_valgus") == pytest.approx(8, abs=5)  # displayed in 5 deg steps
        assert _val(rv, leg, "step_width") == pytest.approx(50, abs=5)  # feet under the hip joints
    assert rv["meta"]["metrics_version"] == rm.METRICS_VERSION
    assert rv["symmetry"]["available"]
    assert rv["symmetry"]["band"] == "symmetric"


def test_stance_and_midstance_are_reported_as_percent_of_cycle():
    rv = _run()
    leg = rv["legs"]["left"]
    assert 30 <= leg["stance_pct"] <= 55
    assert leg["midstance_pct"] == pytest.approx(leg["stance_pct"] / 2, abs=3)
    # hip drop and step width span all of stance; knee alignment its first 60%.
    assert leg["experimental"]["hip_drop"]["window_pct"] == [0.0, leg["stance_pct"]]
    assert leg["step_width"]["window_pct"] == [0.0, leg["stance_pct"]]
    assert leg["knee_valgus"]["window_pct"][1] == pytest.approx(leg["stance_pct"] * 0.6, abs=0.2)
    assert leg["experimental"]["pronation"]["window_pct"] == [0.0, leg["midstance_pct"]]


def test_result_is_json_serialisable():
    json.dumps(_run())


# ---- Asymmetry ---------------------------------------------------------------
def test_hip_drop_asymmetry_is_attributed_to_the_right_leg_and_lowers_symmetry():
    rv = _run(hip_drop_left=3.0, hip_drop_right=12.0, valgus_left=5.0, valgus_right=20.0)
    assert _val(rv, "right", "hip_drop") > _val(rv, "left", "hip_drop") + 4
    assert _val(rv, "right", "knee_valgus") > _val(rv, "left", "knee_valgus")
    assert rv["symmetry"]["band"] != "symmetric"
    assert rv["symmetry"]["score"] < _run()["symmetry"]["score"]


# ---- Normalised to % of gait cycle, not time (rear is not synchronised) ------
@pytest.mark.parametrize("start_phase", [0.13, 0.5, 0.87])
def test_results_do_not_depend_on_where_in_the_cycle_the_clip_starts(start_phase):
    base, shifted = _run(), _run(start_phase=start_phase)
    assert shifted["status"] == "ok"
    for leg in ("left", "right"):
        for metric in rm.METRICS:
            assert abs(_val(shifted, leg, metric) - _val(base, leg, metric)) <= 5
    assert shifted["meta"]["synchronized_with_side_view"] is False
    assert shifted["meta"]["cycle_normalisation"] == "percent_gait_cycle"


def test_curves_are_sampled_on_a_percent_of_cycle_grid():
    rv = _run()
    curves = rv["curves"]
    assert curves["step_pct"] == 5
    hd = curves["left"]["hip_drop_deg"]
    assert len(hd) == 21
    mid_idx = round(rv["legs"]["left"]["midstance_pct"] / 5)
    assert hd[mid_idx] == pytest.approx(6, abs=2.5)          # peak drop near mid-stance
    assert hd[mid_idx] > hd[(mid_idx + 10) % 21]             # contralateral stance: no drop


# ---- Overground: runner drifting away from the camera ------------------------
def test_ankle_drift_from_running_away_does_not_break_cycle_detection():
    rv = _run(ankle_drift_per_frame=-0.0002)
    assert rv["status"] in ("ok", "low_confidence")
    assert rv["legs"]["left"]["cycles_usable"] >= 8
    assert _val(rv, "left", "hip_drop") == pytest.approx(6, abs=3)


# ---- BlazePose left/right swaps ------------------------------------------------
def test_globally_swapped_labels_are_corrected_and_flagged():
    truth = _run(hip_drop_left=3.0, hip_drop_right=12.0)
    swapped = rm.compute_rear_metrics(
        swap_left_right(make_rear_frames(hip_drop_left=3.0, hip_drop_right=12.0)), FPS
    )
    assert swapped["meta"]["left_right_labels_swapped"] is True
    assert _val(swapped, "left", "hip_drop") == pytest.approx(_val(truth, "left", "hip_drop"), abs=2)
    assert _val(swapped, "right", "hip_drop") == pytest.approx(_val(truth, "right", "hip_drop"), abs=2)


def test_frames_contradicting_the_majority_ordering_are_dropped_not_averaged_in():
    frames = make_rear_frames()
    flipped = swap_left_right(frames)
    mixed = [f if i % 5 else flipped[i] for i, f in enumerate(frames)]  # 20% stray swaps
    rv = rm.compute_rear_metrics(mixed, FPS)
    assert rv["meta"]["left_right_consistency"] == pytest.approx(0.8, abs=0.02)
    assert rv["status"] != "insufficient_data"
    assert _val(rv, "left", "hip_drop") == pytest.approx(6, abs=3)


def test_left_right_ordering_that_is_a_coin_flip_reports_nothing():
    frames = make_rear_frames()
    flipped = swap_left_right(frames)
    mixed = [flipped[i] if i % 2 else frames[i] for i in range(len(frames))]
    rv = rm.compute_rear_metrics(mixed, FPS)
    assert rv["status"] == "insufficient_data"
    assert rv["confidence_gate"]["reason"] == "unreliable_left_right"
    assert not rv["legs"]["left"]["knee_valgus"]["available"]


# ---- Never blocks: insufficient / empty data -----------------------------------
def test_too_few_cycles_is_insufficient_data_with_a_user_message():
    rv = _run(n_frames=int(FPS * 1.5) + 21)  # ~2-3 cycles
    assert rv["status"] == "insufficient_data"
    assert rv["confidence_gate"]["reason"] == "insufficient_cycles"
    assert "stride" in rv["confidence_gate"]["user_message"]
    assert rv["symmetry"]["available"] is False
    assert rv["curves"] is None


def test_no_pose_or_no_frames_returns_a_well_formed_empty_rear_view():
    for frames, fps in (([], FPS), ([{"frame_idx": i, "landmarks": None} for i in range(50)], FPS), (make_rear_frames(60), 0)):
        rv = rm.compute_rear_metrics(frames, fps)
        assert rv["status"] == "insufficient_data"
        assert set(rv["legs"]) == {"left", "right"}
        json.dumps(rv)


def test_short_clip_is_low_confidence_but_reported():
    rv = _run(n_frames=CYCLE_FRAMES * 7 + 5)
    assert rv["status"] == "low_confidence"
    assert rv["legs"]["left"]["knee_valgus"]["available"]



# ---- Wider bands + pattern framing (valgus is not a precise angle) -----------------
def test_valgus_is_coarse_flagged_with_its_error_margin_and_disclaimer():
    obj = _run(valgus_left=10.0)["legs"]["left"]["knee_valgus"]
    assert obj["value_deg"] % 5 == 0
    assert obj["error_margin_deg"] is None
    assert "pattern, not a precise angle" in obj["disclaimer"]
    assert obj["confidence"]["tier"] in ("low", "moderate")


def test_pronation_proxy_never_reads_high_confidence():
    for kw in ({}, {"pronation_left": 12.0}):
        assert _run(**kw)["legs"]["left"]["experimental"]["pronation"]["confidence"]["tier"] == "low"


def test_implausible_metric_is_dropped_alone_not_the_whole_report():
    rv = _run(pronation_left=50.0, pronation_right=50.0)
    # atan of a huge heel offset is still a finite angle; it must not survive the bound.
    assert rv["legs"]["left"]["experimental"]["pronation"] == {"available": False, "reason": "implausible"}
    assert rv["legs"]["left"]["knee_valgus"]["available"]
    assert rv["status"] in ("ok", "low_confidence")


def test_low_visibility_lowers_confidence_scores():
    good = _run()["legs"]["left"]["knee_valgus"]["confidence"]["score"]
    poor = _run(visibility=0.6)["legs"]["left"]["knee_valgus"]["confidence"]["score"]
    assert poor < good


# ---- Phase 2 signal processing: tilt cancellation, smoothing, peaks ---------------
@pytest.mark.parametrize("roll", [3.0, -6.0])
def test_camera_roll_no_longer_fakes_asymmetry(roll):
    """A tilted phone used to add +roll to one leg's hip drop and -roll to the
    other. Measured from each leg's own initial contact it cancels out."""
    level, tilted = _run(), _run(camera_roll_deg=roll)
    for leg in ("left", "right"):
        assert _val(tilted, leg, "hip_drop") == pytest.approx(_val(level, leg, "hip_drop"), abs=1)
    assert tilted["symmetry"]["band"] == "symmetric"
    assert tilted["meta"]["tilt_offset_deg"] == pytest.approx(roll, abs=1)
    # Knee alignment is an angle between two segments: rotation-invariant.
    for leg in ("left", "right"):
        assert _val(tilted, leg, "knee_valgus") == _val(level, leg, "knee_valgus")


def test_hip_drop_is_measured_from_the_leg_s_own_foot_strike():
    rv = _run(hip_drop_left=4.0, hip_drop_right=12.0)
    assert _val(rv, "left", "hip_drop") == pytest.approx(4, abs=1)
    # Smoothing softens a sharp synthetic peak by ~5%; real pelvic drop is broader.
    assert _val(rv, "right", "hip_drop") == pytest.approx(12, abs=1.5)
    assert _obj(rv, "right", "hip_drop")["pattern"] == "pronounced"
    assert _obj(rv, "left", "hip_drop")["pattern"] == "typical"


def test_smoothing_keeps_noisy_landmarks_usable():
    noisy = _run(noise=0.003, seed=1)
    assert noisy["status"] in ("ok", "low_confidence")
    for leg in ("left", "right"):
        assert _val(noisy, leg, "hip_drop") == pytest.approx(6, abs=3)
        assert _obj(noisy, leg, "hip_drop")["ci95_deg"] < 3


def test_smoothing_filters_jitter_without_moving_real_points():
    frames = make_rear_frames(noise=0.004, seed=2)
    clean = make_rear_frames()
    smoothed = rm._smooth_landmarks(frames, FPS)
    def err(fs):
        return sum(abs(f["landmarks"][23]["y"] - c["landmarks"][23]["y"]) for f, c in zip(fs, clean))

    assert err(smoothed) < 0.7 * err(frames)
    assert frames[0]["landmarks"][23]["y"] != smoothed[0]["landmarks"][23]["y"]  # new dicts, input untouched
    assert rm._smooth_landmarks(frames, 12.0) is frames  # too low a frame rate for an 8 Hz cutoff


def test_varus_knee_reports_its_most_varus_frame():
    assert rm._peak_in_direction([-3, -8, -5]) == -8
    assert rm._peak_in_direction([2, 9, 4]) == 9
    assert rm._peak_in_direction([None, None]) is None
    assert _val(_run(valgus_left=-12.0, valgus_right=-12.0), "left", "knee_valgus") < 0


# ---- Phase 3: step width -------------------------------------------------------------
def test_step_width_patterns():
    for offset, pattern in ((50.0, "typical"), (5.0, "narrow"), (-20.0, "crossover")):
        rv = _run(foot_offset_pct=offset)
        assert _val(rv, "left", "step_width") == pytest.approx(offset, abs=5)
        assert rv["legs"]["left"]["step_width"]["pattern"] == pattern
    # Moving the feet doesn't change knee alignment (knee stays on the hip-ankle line + offset).
    assert _val(_run(foot_offset_pct=-20.0), "left", "knee_valgus") == _val(_run(), "left", "knee_valgus")


def test_pronation_and_hip_drop_are_experimental_and_out_of_symmetry():
    rv = _run()
    for metric in ("pronation", "hip_drop"):
        assert metric not in rv["legs"]["left"]
        assert rv["legs"]["left"]["experimental"][metric]["available"]
    assert set(rv["symmetry"]["components"]) == {"knee_valgus", "step_width"}
    assert set(rv["curves"]["left"]) == {"hip_drop_deg", "knee_valgus_deg"}

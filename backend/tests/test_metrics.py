"""Unit tests for backend.metrics (compute_metrics). No file I/O, DB, or Redis."""
from backend.metrics import _compute_summary, compute_metrics

# MediaPipe-style indices
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_KNEE, RIGHT_KNEE = 25, 26
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12


def _landmark(x, y, visibility=1.0):
    return {"x": x, "y": y, "visibility": visibility}


def _pose_frame(frame_idx, left_ankle_y, right_ankle_y, hip_y=0.5, head_y=0.2):
    """Minimal pose frame with optional hip/head for scale. Ankle y drives foot-strike detection."""
    return {
        "frame_idx": frame_idx,
        "landmarks": {
            0: _landmark(0.5, head_y),
            LEFT_SHOULDER: _landmark(0.4, 0.35),
            RIGHT_SHOULDER: _landmark(0.6, 0.35),
            LEFT_HIP: _landmark(0.45, hip_y),
            RIGHT_HIP: _landmark(0.55, hip_y),
            LEFT_KNEE: _landmark(0.45, 0.65),
            RIGHT_KNEE: _landmark(0.55, 0.65),
            LEFT_ANKLE: _landmark(0.45, left_ankle_y),
            RIGHT_ANKLE: _landmark(0.55, right_ankle_y),
        },
    }


def _frames_with_strikes_at(strike_indices_left, num_frames, hip_y=0.5, head_y=0.2, hip_y_fn=None):
    """Build pose_frames so left ankle has local MAXIMA at strike_indices_left.

    Detection now uses local maxima: foot on ground = highest y value in frame.
      strike frames  : left_y = 0.85  (foot down, prominent peak)
      within-6 frames: left_y = 0.76  (transitioning, forms the peak flanks)
      all others     : left_y = 0.65  (foot in air, low y)
    Right ankle is always at ~0.65 so it won't produce any detected strikes.
    """
    strike_set = set(strike_indices_left)
    out = []
    for i in range(num_frames):
        if i in strike_set:
            left_y = 0.85   # foot on ground → local maximum
        elif any(0 < abs(i - s) <= 6 for s in strike_set):
            left_y = 0.76   # transitioning
        else:
            left_y = 0.65 + i * 1e-6   # foot in air → low y
        right_y = 0.65 + i * 1e-6
        hy = hip_y_fn(i) if hip_y_fn else hip_y
        out.append(_pose_frame(i, left_y, right_y, hip_y=hy, head_y=head_y))
    return out


# ---- Cadence ----
def test_cadence_single_stride_30fps():
    """One stride of 30 frames at 30 fps -> cadence 120 (2 steps per second)."""
    strike_indices = [10, 40]
    frames = _frames_with_strikes_at(strike_indices, 50)
    result = compute_metrics(frames, 175, 30.0)
    assert "summary" in result
    assert result["summary"].get("cadence_avg") is not None
    duration_sec = (40 - 10) / 30.0
    expected_cadence = 2 * 60 / duration_sec
    assert abs(result["summary"]["cadence_avg"] - expected_cadence) < 1.0


def test_cadence_two_strides():
    """Two strides -> average cadence from both."""
    strike_indices = [10, 40, 70]
    frames = _frames_with_strikes_at(strike_indices, 85)
    result = compute_metrics(frames, 175, 30.0)
    assert result["summary"].get("cadence_avg") is not None
    assert result["summary"].get("num_strides") == 2


def test_cadence_high_fps_shorter_duration():
    """60 fps, same frame span -> higher cadence (shorter duration per stride)."""
    strike_indices = [10, 40]
    frames = _frames_with_strikes_at(strike_indices, 50)
    result_30 = compute_metrics(frames, 175, 30.0)
    result_60 = compute_metrics(frames, 175, 60.0)
    assert result_60["summary"]["cadence_avg"] > result_30["summary"]["cadence_avg"]


# ---- Vertical oscillation ----
def _hip_y_bump_08(i):
    return 0.5 + (0.08 if 15 <= i <= 25 else 0)


def test_vertical_oscillation_from_hip_variation():
    """Hip y varies within stride -> non-zero vertical_osc_avg_cm."""
    strike_indices = [10, 40]
    frames = _frames_with_strikes_at(strike_indices, 50, hip_y_fn=_hip_y_bump_08)
    result = compute_metrics(frames, 175, 30.0)
    assert result["summary"].get("vertical_osc_avg_cm") is not None
    assert result["summary"]["vertical_osc_avg_cm"] > 0


def test_vertical_oscillation_flat_hip():
    """No hip movement -> zero vertical oscillation."""
    strike_indices = [10, 40]
    frames = _frames_with_strikes_at(strike_indices, 50, hip_y=0.5)
    result = compute_metrics(frames, 175, 30.0)
    assert result["summary"].get("vertical_osc_avg_cm") is not None
    assert result["summary"]["vertical_osc_avg_cm"] == 0


def _hip_y_bump_05(i):
    return 0.5 + (0.05 if 15 <= i <= 25 else 0)


def test_vertical_oscillation_scales_with_height():
    """Larger height_cm with same normalized movement -> larger vertical_osc_avg_cm."""
    strike_indices = [10, 40]
    frames = _frames_with_strikes_at(strike_indices, 50, hip_y_fn=_hip_y_bump_05)
    r175 = compute_metrics(frames, 175, 30.0)
    r160 = compute_metrics(frames, 160, 30.0)
    assert r175["summary"]["vertical_osc_avg_cm"] > 0
    assert r160["summary"]["vertical_osc_avg_cm"] > 0


# ---- Stride detection ----
def test_stride_detection_count():
    """Number of strides matches (left strikes - 1)."""
    strike_indices = [10, 40, 70, 100]
    frames = _frames_with_strikes_at(strike_indices, 110)
    result = compute_metrics(frames, 175, 30.0)
    assert len(result["strides"]) == 3


def test_stride_detection_single_strike_no_strides():
    """Only one left strike -> no full stride."""
    strike_indices = [10]
    frames = _frames_with_strikes_at(strike_indices, 25)
    result = compute_metrics(frames, 175, 30.0)
    assert result["strides"] == []
    assert result["summary"] == {}


def test_stride_detection_frame_indices():
    """Strides have correct start_frame and end_frame from left strikes."""
    strike_indices = [10, 40, 70]
    frames = _frames_with_strikes_at(strike_indices, 80)
    result = compute_metrics(frames, 175, 30.0)
    assert len(result["strides"]) >= 2
    assert result["strides"][0]["start_frame"] == 10
    assert result["strides"][0]["end_frame"] == 40


# ---- Edge cases ----
def test_empty_pose_frames_returns_empty_results():
    """Empty pose_frames -> empty summary and strides."""
    result = compute_metrics([], 175, 30.0)
    assert result["summary"] == {}
    assert result["strides"] == []
    assert result["meta"]["height_cm"] == 175


def test_no_valid_landmarks_returns_empty():
    """Frames with no landmarks -> empty results."""
    frames = [{"frame_idx": i, "landmarks": None} for i in range(10)]
    result = compute_metrics(frames, 175, 30.0)
    assert result["summary"] == {}
    assert result["strides"] == []


def test_zero_fps_returns_empty():
    """fps 0 -> empty results."""
    frames = _frames_with_strikes_at([10, 40], 50)
    result = compute_metrics(frames, 175, 0)
    assert result["summary"] == {}
    assert result["strides"] == []


def test_negative_fps_returns_empty():
    """Negative fps -> empty results."""
    frames = _frames_with_strikes_at([10, 40], 50)
    result = compute_metrics(frames, 175, -1.0)
    assert result["summary"] == {}
    assert result["strides"] == []


# ---- Visibility filtering ----

def _pose_frame_with_low_vis_ankles(frame_idx, left_ankle_y, right_ankle_y, visibility=0.1):
    """Pose frame where ankle landmarks have low visibility (motion blur simulation)."""
    return {
        "frame_idx": frame_idx,
        "landmarks": {
            0: _landmark(0.5, 0.2),
            LEFT_SHOULDER: _landmark(0.4, 0.35),
            RIGHT_SHOULDER: _landmark(0.6, 0.35),
            LEFT_HIP: _landmark(0.45, 0.5),
            RIGHT_HIP: _landmark(0.55, 0.5),
            LEFT_KNEE: _landmark(0.45, 0.65),
            RIGHT_KNEE: _landmark(0.55, 0.65),
            LEFT_ANKLE: _landmark(0.45, left_ankle_y, visibility=visibility),
            RIGHT_ANKLE: _landmark(0.55, right_ankle_y, visibility=visibility),
        },
    }


def test_low_visibility_frames_ignored():
    """Frames with low ankle visibility are skipped — blurry frames don't corrupt the signal."""
    strike_set = {10, 40}
    frames = []
    for i in range(50):
        if i in strike_set:
            frames.append(_pose_frame(i, 0.85, 0.65))   # high-vis strike frame
        elif any(0 < abs(i - s) <= 6 for s in strike_set):
            frames.append(_pose_frame(i, 0.76, 0.65))   # high-vis flank
        else:
            # Simulate blurry airborne frames with random-ish noisy y and low visibility
            noisy_y = 0.85 - (i % 5) * 0.03            # would look like spurious peaks if trusted
            frames.append(_pose_frame_with_low_vis_ankles(i, noisy_y, 0.65, visibility=0.2))
    result = compute_metrics(frames, 175, 30.0)
    # Should still detect the two valid strikes and produce one stride
    assert result["summary"].get("cadence_avg") is not None
    assert result["summary"]["num_strides"] >= 1


def test_right_ankle_fallback():
    """If left ankle produces no strides but right ankle does, fall back to right."""
    strike_set = {15, 50, 85}
    frames = []
    for i in range(100):
        # Left ankle has no visibility — always blurry
        if i in strike_set:
            right_y = 0.85
        elif any(0 < abs(i - s) <= 6 for s in strike_set):
            right_y = 0.76
        else:
            right_y = 0.65 + i * 1e-6
        frames.append({
            "frame_idx": i,
            "landmarks": {
                0: _landmark(0.5, 0.2),
                LEFT_SHOULDER: _landmark(0.4, 0.35),
                RIGHT_SHOULDER: _landmark(0.6, 0.35),
                LEFT_HIP: _landmark(0.45, 0.5),
                RIGHT_HIP: _landmark(0.55, 0.5),
                LEFT_KNEE: _landmark(0.45, 0.65),
                RIGHT_KNEE: _landmark(0.55, 0.65),
                LEFT_ANKLE: _landmark(0.45, 0.65 + i * 1e-6, visibility=0.1),  # never reliable
                RIGHT_ANKLE: _landmark(0.55, right_y),
            },
        })
    result = compute_metrics(frames, 175, 30.0)
    assert result["summary"].get("cadence_avg") is not None
    assert result["summary"]["num_strides"] >= 2


# ---- Spurious double-detection (cadence spikes) ----
def test_close_spurious_strike_is_suppressed_not_counted_as_a_stride():
    """A spurious extra 'strike' close to a real one (landmark jitter, motion
    blur) must not produce an implausible-cadence stride. Regression test for
    a bug where an extra detection 9 frames (0.3s @ 30fps) after a real one
    was accepted as its own stride, implying ~400 spm — see metrics.py's
    _suppress_close_peaks and the tightened _STRIDE_MIN_SEC."""
    frames = _frames_with_strikes_at([10, 40, 49, 80], 100)
    result = compute_metrics(frames, 175, 30.0)
    cadences = [s["cadence"] for s in result["strides"]]
    assert all(c <= 250 for c in cadences), cadences


def test_no_implausibly_fast_stride_from_any_detected_pair():
    """Every detected stride's implied cadence must stay within a
    physiologically plausible ceiling — nothing above elite sprint cadence."""
    strike_indices = [10, 40, 70, 100, 130]
    frames = _frames_with_strikes_at(strike_indices, 150)
    result = compute_metrics(frames, 175, 30.0)
    for s in result["strides"]:
        assert s["cadence"] <= 250, s


# ---- Knee flexion semantics ----
def test_knee_flexion_is_deviation_from_straight_not_raw_joint_angle():
    """knee_angle_strike_deg must be degrees bent from a straight leg (small
    = too straight, large = well bent) — the semantic every threshold and
    the dashboard/frontend assume. The test fixture's hip/knee/ankle are
    collinear (same x) at every frame, i.e. a straight leg (~180° raw joint
    angle) — this must read as LOW flexion (~0°), not ~180."""
    frames = _frames_with_strikes_at([10, 40], 60)
    result = compute_metrics(frames, 175, 30.0)
    knee = result["summary"].get("knee_angle_strike_avg_deg")
    assert knee is not None
    assert knee < 15, f"expected low flexion for a straight (collinear) leg, got {knee}"


def test_knee_flexion_low_triggers_too_straight_heuristic_flag():
    """A straight-leg-at-strike reading must actually trip the knee-flexion
    flag end to end (compute_metrics -> evaluate_heuristics), not just look
    right in isolation — this is the exact chain the dashboard/chart relies on."""
    from backend.heuristics import evaluate_heuristics

    frames = _frames_with_strikes_at([10, 40], 60)
    result = compute_metrics(frames, 175, 30.0)
    flags = evaluate_heuristics(result)
    metrics_flagged = {f["metric"] for f in flags}
    assert "knee_flexion_at_strike" in metrics_flagged, flags


# ---- Aggregation robustness: outlier rejection + median (Part 2) ----
# These test _compute_summary directly rather than through the full
# pose-frame -> detection pipeline: a genuine 360 spm stride right next to
# genuine 180 spm ones is exactly the kind of closely-spaced spurious
# detection _suppress_close_peaks (see above) already prevents from ever
# reaching _build_strides in real footage. The aggregation robustness this
# covers is a second, independent line of defense — for outliers that *do*
# pass detection (e.g. one frame's landmarks are briefly wrong, corrupting
# a single stride's reading without an implausible duration) — so it's
# tested at the unit it actually lives in.
def _stride(cadence, vertical_osc_cm=8.0, knee=25.0, foot=5.0, trunk=5.0):
    return {
        "cadence": cadence,
        "vertical_osc_cm": vertical_osc_cm,
        "knee_angle_strike_deg": knee,
        "foot_strike_position_cm": foot,
        "trunk_lean_deg": trunk,
        "duration_sec": 120.0 / cadence,
    }


def test_outlier_strides_rejected_before_aggregating():
    """[180,180,180,360,180,90,180] -> aggregate near 180, not the arithmetic
    mean (~192.9 spm). The 360 and 90 spm strides' intervals deviate more
    than _OUTLIER_DURATION_DEVIATION (40%) from the median interval and must
    be dropped before aggregating."""
    cadences = [180, 180, 180, 360, 180, 90, 180]
    strides = [_stride(c) for c in cadences]
    summary = _compute_summary(strides)
    assert summary["cadence_avg"] == 180.0
    assert summary["num_strides"] == 5, "360 and 90 spm strides should be rejected as outliers"
    assert summary["num_strides_detected"] == 7


def test_no_outlier_rejection_with_only_one_stride():
    """A single stride can't deviate from 'the median' of itself — must not
    be dropped for lack of company."""
    summary = _compute_summary([_stride(180)])
    assert summary["num_strides"] == 1
    assert summary["cadence_avg"] == 180.0


def test_normal_variation_is_not_treated_as_outliers():
    """Realistic stride-to-stride cadence variation (well within 40% of the
    median interval) must not be rejected — only genuinely implausible
    spikes should be."""
    cadences = [178, 182, 175, 180, 185, 179, 181]
    strides = [_stride(c) for c in cadences]
    summary = _compute_summary(strides)
    assert summary["num_strides"] == len(cadences)
    assert summary["num_strides_detected"] == len(cadences)


# ---- fps must be the *effective* (post-subsampling) rate, not the source
# video's native rate — regression test for the GAIT_TARGET_FPS bug ----
def _subsampled_running_frames(effective_fps, stride_interval_sec, duration_sec):
    """Pose frames as they'd look after job_runner.py's frame_skip decimation
    (GAIT_TARGET_FPS): evenly spaced at effective_fps, with a real timestamp
    per frame and an ankle-y strike pattern repeating every stride_interval_sec."""
    dt = 1.0 / effective_fps
    n = int(duration_sec / dt)
    period_samples = stride_interval_sec / dt
    frames = []
    for i in range(n):
        is_strike = abs(i - round(i / period_samples) * period_samples) < 1
        left_y = 0.85 if is_strike else 0.65
        frames.append({
            "frame_idx": i,
            "timestamp_ms": i * dt * 1000,
            "landmarks": {
                0: _landmark(0.5, 0.2),
                LEFT_SHOULDER: _landmark(0.4, 0.35), RIGHT_SHOULDER: _landmark(0.6, 0.35),
                LEFT_HIP: _landmark(0.45, 0.5), RIGHT_HIP: _landmark(0.55, 0.5),
                LEFT_KNEE: _landmark(0.45, 0.65), RIGHT_KNEE: _landmark(0.55, 0.65),
                LEFT_ANKLE: _landmark(0.45, left_y), RIGHT_ANKLE: _landmark(0.55, 0.65),
            },
        })
    return frames


def test_effective_fps_produces_correct_stride_count_and_cadence():
    """The 'correct' side of the bug: given the actual sampling rate of the
    frames (what job_runner.py now passes after computing effective_fps =
    fps / frame_skip), a realistic 0.7s-interval (~171 spm) 30s clip must
    detect roughly the expected ~40+ strides at the right cadence."""
    frames = _subsampled_running_frames(effective_fps=10, stride_interval_sec=0.7, duration_sec=30)
    result = compute_metrics(frames, 175, fps=10)
    assert result["summary"]["num_strides"] >= 35
    assert abs(result["summary"]["cadence_avg"] - 171) <= 5


def test_native_fps_on_subsampled_frames_undercounts_and_halves_cadence():
    """Regression test for the actual bug: job_runner.py used to pass the
    source video's native fps (e.g. 30, from GAIT_TARGET_FPS's frame_skip
    decimation) instead of the effective sampled rate (e.g. 10) into
    compute_metrics. Every time-based constant in _detect_foot_strikes is in
    units of "array steps per second", so this made them ~3x too wide,
    merging away most real strides and roughly halving cadence -- this is
    what turned "not enough strides" (the confidence gate, correctly firing)
    into an overcorrection: real 30s clips reporting single-digit stride
    counts. Same frames as the test above, wrong fps -- must visibly regress,
    proving the fix in job_runner.py (passing effective_fps) matters."""
    frames = _subsampled_running_frames(effective_fps=10, stride_interval_sec=0.7, duration_sec=30)
    result = compute_metrics(frames, 175, fps=30)  # the bug: native, not effective
    assert result["summary"]["num_strides"] < 20, (
        "expected the native-fps bug to undercount strides significantly; "
        f"got {result['summary']['num_strides']}"
    )
    assert result["summary"]["cadence_avg"] < 171 * 0.7, "expected the halving artifact"

"""Unit tests for backend.metrics (compute_metrics). No file I/O, DB, or Redis."""
from backend.metrics import compute_metrics

# MediaPipe-style indices
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_KNEE, RIGHT_KNEE = 25, 26
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12


def _landmark(x, y):
    return {"x": x, "y": y}


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
    """Build pose_frames so left ankle has strict local minima only at strike_indices_left (radius 3)."""
    strike_set = set(strike_indices_left)
    out = []
    for i in range(num_frames):
        if i in strike_set:
            left_y = 0.75
        elif any(0 < abs(i - s) <= 3 for s in strike_set):
            left_y = 0.76
        else:
            left_y = 0.85 + i * 1e-6
        right_y = 0.85 + i * 1e-6
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

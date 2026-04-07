"""
Compute gait metrics from pose landmark data. Pure functions: accept landmark
series + height_cm and fps, return a results dict matching the results.json
schema (summary, strides). No file I/O.
"""

import math
from datetime import datetime, timezone

_STRIDE_MIN_SEC = 0.25
_STRIDE_MAX_SEC = 1.5

LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_KNEE, RIGHT_KNEE = 25, 26
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12

# MediaPipe landmark 0 is the nose (~93% of standing height from floor).
# Ankle midpoint sits at ~4% of height from floor.
# Nose-to-ankle therefore spans ≈89% of total body height.
_NOSE_TO_ANKLE_FRACTION = 0.89
# Nose-to-hip fallback when ankles are poorly visible (~93% - 47% = 46%).
_NOSE_TO_HIP_FRACTION = 0.46
# Minimum ankle visibility score to prefer the head-to-ankle span.
_ANKLE_VIS_THRESHOLD = 0.5


def compute_metrics(pose_frames, height_cm, fps, video_file=""):
    if not pose_frames or not fps or fps <= 0:
        return _empty_results(height_cm, video_file)

    valid = [p for p in pose_frames if p.get("landmarks")]
    if not valid:
        return _empty_results(height_cm, video_file)

    scale = _pixel_scale_from_height(valid, height_cm)
    strikes_left, strikes_right = _detect_foot_strikes(pose_frames, fps=fps)
    strides = _build_strides(
        pose_frames, strikes_left, strikes_right, scale, fps, height_cm
    )

    if not strides:
        return _empty_results(height_cm, video_file)

    summary = _compute_summary(strides)

    ankle_vis = []
    for p in valid:
        lm = p["landmarks"]
        ankle_vis.append(lm[LEFT_ANKLE].get("visibility", 1.0))
        ankle_vis.append(lm[RIGHT_ANKLE].get("visibility", 1.0))
    fps_score = min(fps / 60.0, 1.0)
    vis_score = sum(ankle_vis) / len(ankle_vis) if ankle_vis else 1.0
    stride_score = min(len(strides) / 5.0, 1.0)
    summary["cadence_confidence"] = round((fps_score + vis_score + stride_score) / 3.0, 3)

    return {
        "meta": {
            "height_cm": height_cm,
            "video_file": video_file,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "fps": fps,
            "num_frames": len(pose_frames),
        },
        "summary": summary,
        "flags": [],
        "strides": strides,
    }


def _empty_results(height_cm, video_file):
    return {
        "meta": {
            "height_cm": height_cm,
            "video_file": video_file,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        },
        "summary": {},
        "flags": [],
        "strides": [],
    }


def _pixel_scale_from_height(pose_frames_with_landmarks, height_cm):
    """Return a scale factor in cm-per-normalised-unit.

    Uses the nose→ankle span when both ankles are clearly visible, which
    spans ≈89% of standing height and provides the most stable reference.
    Falls back to nose→hip (≈46% of height) when ankles are obscured.
    Both paths apply the correct body-proportion fraction so that scale
    errors from torso/limb proportion variance are minimised.
    """
    total = 0.0
    count = 0
    for p in pose_frames_with_landmarks:
        lm = p["landmarks"]
        nose_y = lm[0]["y"]
        ankle_vis_l = lm[LEFT_ANKLE].get("visibility", 0.0)
        ankle_vis_r = lm[RIGHT_ANKLE].get("visibility", 0.0)
        avg_ankle_vis = (ankle_vis_l + ankle_vis_r) / 2.0

        if avg_ankle_vis >= _ANKLE_VIS_THRESHOLD:
            ankle_y = (lm[LEFT_ANKLE]["y"] + lm[RIGHT_ANKLE]["y"]) / 2.0
            norm_span = abs(ankle_y - nose_y)
            real_span_cm = height_cm * _NOSE_TO_ANKLE_FRACTION
        else:
            hip_y = (lm[LEFT_HIP]["y"] + lm[RIGHT_HIP]["y"]) / 2.0
            norm_span = abs(hip_y - nose_y)
            real_span_cm = height_cm * _NOSE_TO_HIP_FRACTION

        if norm_span > 0:
            total += real_span_cm / norm_span
            count += 1

    if count == 0 or total == 0:
        return height_cm
    return total / count


def _savgol_window(fps):
    """Return an odd Savitzky-Golay window length ≈350 ms for the given FPS."""
    window = max(5, int(fps * 0.35))
    if window % 2 == 0:
        window += 1
    return window


def _savgol_or_passthrough(ys, fps=30.0, window=None, polyorder=2):
    """Apply Savitzky-Golay smoothing to a signal that may contain None values.

    The window length scales with FPS so that the effective smoothing duration
    stays constant (~350 ms) regardless of input frame rate.
    """
    if window is None:
        window = _savgol_window(fps)
    if len(ys) < window:
        return ys
    try:
        from scipy.signal import savgol_filter
        import numpy as np
    except ImportError:
        return ys

    filled = list(ys)
    for i in range(1, len(filled)):
        if filled[i] is None and filled[i - 1] is not None:
            filled[i] = filled[i - 1]
    for i in range(len(filled) - 2, -1, -1):
        if filled[i] is None and filled[i + 1] is not None:
            filled[i] = filled[i + 1]
    if any(v is None for v in filled):
        return ys

    smoothed = savgol_filter(np.array(filled, dtype=float), window, polyorder)
    return [None if ys[i] is None else float(smoothed[i]) for i in range(len(ys))]


def _detect_foot_strikes(pose_frames, fps=30.0):
    """Detect per-foot strike frames as local minima of ankle Y (normalised coords).

    In image coordinates Y increases downward, so the ankle reaches its
    minimum Y value at peak swing — a sharp, repeatable signal that works
    well for cadence/stride segmentation.  The minimum distance between
    detected events is clamped to _STRIDE_MIN_SEC * fps so that noise near
    the trough cannot produce spurious double-detections.
    """
    left_ys = []
    right_ys = []
    for p in pose_frames:
        lm = p["landmarks"]
        if lm is None:
            left_ys.append(None)
            right_ys.append(None)
            continue
        left_ys.append(lm[LEFT_ANKLE]["y"])
        right_ys.append(lm[RIGHT_ANKLE]["y"])

    left_ys = _savgol_or_passthrough(left_ys, fps=fps)
    right_ys = _savgol_or_passthrough(right_ys, fps=fps)

    # Minimum frames separating consecutive strikes for the same foot.
    min_distance = max(3, int(_STRIDE_MIN_SEC * fps))

    def find_strikes(ys):
        try:
            from scipy.signal import find_peaks
            import numpy as np

            arr = np.array(
                [y if y is not None else float("nan") for y in ys], dtype=float
            )
            # Interpolate over NaN gaps so find_peaks sees a continuous signal.
            nans = np.isnan(arr)
            if nans.all():
                return []
            if nans.any():
                x = np.arange(len(arr))
                arr[nans] = np.interp(x[nans], x[~nans], arr[~nans])
            # Negate: find_peaks finds maxima; negating turns minima into maxima.
            # prominence filters out tiny SG smoothing artifacts — real ankle dips
            # are ≥0.10 normalised units deep; ringing noise is typically <0.001.
            peaks, _ = find_peaks(-arr, distance=min_distance, prominence=0.03)
            return peaks.tolist()
        except ImportError:
            # Pure-Python fallback: manual local-minimum search.
            radius = max(3, min_distance // 2)
            out = []
            for i in range(radius, len(ys) - radius):
                if ys[i] is None:
                    continue
                if all(
                    ys[i] <= ys[j]
                    for j in range(i - radius, i + radius + 1)
                    if ys[j] is not None
                ):
                    out.append(i)
            return out

    left = find_strikes(left_ys)
    right = find_strikes(right_ys)
    return left, right


def _build_strides(pose_frames, strikes_left, strikes_right, scale, fps, height_cm):
    ts_lookup = {p["frame_idx"]: p["timestamp_ms"] for p in pose_frames if p.get("timestamp_ms") is not None}

    strides = []
    for k in range(len(strikes_left) - 1):
        start_frame = strikes_left[k]
        end_frame = strikes_left[k + 1]

        if start_frame in ts_lookup and end_frame in ts_lookup:
            duration_sec = (ts_lookup[end_frame] - ts_lookup[start_frame]) / 1000.0
        else:
            duration_sec = (end_frame - start_frame) / fps if fps else 0

        if not (_STRIDE_MIN_SEC <= duration_sec <= _STRIDE_MAX_SEC):
            continue

        stride_frames = [p for p in pose_frames if start_frame <= p["frame_idx"] < end_frame]
        if not stride_frames:
            continue
        d = _metrics_for_stride(stride_frames, start_frame, end_frame, scale, height_cm, duration_sec)
        d["stride_num"] = k + 1
        d["start_frame"] = start_frame
        d["end_frame"] = end_frame
        strides.append(d)
    return strides


def _metrics_for_stride(stride_frames, start_frame, end_frame, scale, height_cm, duration_sec):
    steps_per_min = (2 * 60 / duration_sec) if duration_sec > 0 else 0

    hip_ys = []
    for p in stride_frames:
        if p["landmarks"] is None:
            continue
        lm = p["landmarks"]
        hy = (lm[LEFT_HIP]["y"] + lm[RIGHT_HIP]["y"]) / 2
        hip_ys.append(hy)
    vertical_osc_norm = (max(hip_ys) - min(hip_ys)) if hip_ys else 0
    vertical_osc_cm = vertical_osc_norm * scale

    strike_frame = _frame_at_index(stride_frames, start_frame)

    # Average left and right knee angles; use whichever side(s) are available.
    knee_l = _knee_angle_at_strike(strike_frame, left=True)
    knee_r = _knee_angle_at_strike(strike_frame, left=False)
    available_knees = [k for k in [knee_l, knee_r] if k is not None]
    knee_angle = sum(available_knees) / len(available_knees) if available_knees else None

    foot_strike_cm = _foot_strike_position_cm(strike_frame, scale)
    trunk_lean_deg = _trunk_lean_degrees(strike_frame)

    return {
        "cadence": round(steps_per_min, 1),
        "vertical_osc_cm": round(vertical_osc_cm, 2),
        "knee_angle_strike_deg": round(knee_angle, 1) if knee_angle is not None else None,
        "foot_strike_position_cm": round(foot_strike_cm, 2) if foot_strike_cm is not None else None,
        "trunk_lean_deg": round(trunk_lean_deg, 1) if trunk_lean_deg is not None else None,
        "duration_sec": round(duration_sec, 3),
    }


def _frame_at_index(stride_frames, frame_idx):
    for p in stride_frames:
        if p["frame_idx"] == frame_idx:
            return p
    return stride_frames[0] if stride_frames else None


def _angle_between_vectors(v1, v2):
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    m1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
    m2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
    if m1 * m2 == 0:
        return None
    cos_a = max(-1, min(1, dot / (m1 * m2)))
    return math.degrees(math.acos(cos_a))


def _knee_angle_at_strike(frame_data, left=True):
    if frame_data is None or frame_data.get("landmarks") is None:
        return None
    lm = frame_data["landmarks"]
    if left:
        hip, knee, ankle = LEFT_HIP, LEFT_KNEE, LEFT_ANKLE
    else:
        hip, knee, ankle = RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
    v1 = (lm[hip]["x"] - lm[knee]["x"], lm[hip]["y"] - lm[knee]["y"])
    v2 = (lm[ankle]["x"] - lm[knee]["x"], lm[ankle]["y"] - lm[knee]["y"])
    return _angle_between_vectors(v1, v2)


def _foot_strike_position_cm(frame_data, scale):
    if frame_data is None or frame_data.get("landmarks") is None:
        return None
    lm = frame_data["landmarks"]
    hip_x = (lm[LEFT_HIP]["x"] + lm[RIGHT_HIP]["x"]) / 2
    ankle_x = lm[LEFT_ANKLE]["x"]
    dx = ankle_x - hip_x
    return abs(dx) * scale if scale else None


def _trunk_lean_degrees(frame_data):
    if frame_data is None or frame_data.get("landmarks") is None:
        return None
    lm = frame_data["landmarks"]
    shoulder_x = (lm[LEFT_SHOULDER]["x"] + lm[RIGHT_SHOULDER]["x"]) / 2
    shoulder_y = (lm[LEFT_SHOULDER]["y"] + lm[RIGHT_SHOULDER]["y"]) / 2
    hip_x = (lm[LEFT_HIP]["x"] + lm[RIGHT_HIP]["x"]) / 2
    hip_y = (lm[LEFT_HIP]["y"] + lm[RIGHT_HIP]["y"]) / 2
    dx = shoulder_x - hip_x
    dy = shoulder_y - hip_y
    vertical = (0, -1)
    trunk = (dx, dy)
    angle = _angle_between_vectors(vertical, trunk)
    if angle is None:
        return None
    if dx > 0:
        return angle
    return -angle


def _compute_summary(strides):
    if not strides:
        return {}
    cadences = [s["cadence"] for s in strides]
    oscs = [s["vertical_osc_cm"] for s in strides]
    knees = [s["knee_angle_strike_deg"] for s in strides if s.get("knee_angle_strike_deg") is not None]
    foots = [s["foot_strike_position_cm"] for s in strides if s.get("foot_strike_position_cm") is not None]
    trunks = [s["trunk_lean_deg"] for s in strides if s.get("trunk_lean_deg") is not None]
    return {
        "cadence_avg": round(sum(cadences) / len(cadences), 1),
        "vertical_osc_avg_cm": round(sum(oscs) / len(oscs), 2),
        "knee_angle_strike_avg_deg": round(sum(knees) / len(knees), 1) if knees else None,
        "foot_strike_position_avg_cm": round(sum(foots) / len(foots), 2) if foots else None,
        "trunk_lean_avg_deg": round(sum(trunks) / len(trunks), 1) if trunks else None,
        "num_strides": len(strides),
    }

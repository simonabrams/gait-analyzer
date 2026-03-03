"""
Compute gait metrics from pose landmark data. Pure functions: accept landmark
series + height_cm and fps, return a results dict matching the results.json
schema (summary, strides). No file I/O. In a web app, called after
pose_extractor with user-provided height and video fps.
"""

import math
from datetime import datetime, timezone

# Indices matching pose_extractor
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_KNEE, RIGHT_KNEE = 25, 26
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12


def compute_metrics(pose_frames, height_cm, fps, video_file=""):
    """
    Build full results dict: meta, summary, strides. Does not add flags
    (heuristics module does that).

    Args:
        pose_frames: List from pose_extractor.extract_poses (frame_idx, landmarks).
        height_cm: User height in cm for scaling to real-world distances.
        fps: Video frames per second.
        video_file: Optional path/name for meta.

    Returns:
        Dict with meta, summary, flags (empty), strides.
    """
    if not pose_frames or not fps or fps <= 0:
        return _empty_results(height_cm, video_file)

    valid = [p for p in pose_frames if p.get("landmarks")]
    if not valid:
        return _empty_results(height_cm, video_file)

    scale = _pixel_scale_from_height(valid, height_cm)
    strikes_left, strikes_right = _detect_foot_strikes(pose_frames)
    strides = _build_strides(
        pose_frames, strikes_left, strikes_right, scale, fps, height_cm
    )

    if not strides:
        return _empty_results(height_cm, video_file)

    summary = _compute_summary(strides)
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
    """Use average vertical body extent (hip to head) in normalized coords as 1 unit = height_cm."""
    total = 0
    count = 0
    for p in pose_frames_with_landmarks:
        lm = p["landmarks"]
        hip_y = (lm[LEFT_HIP]["y"] + lm[RIGHT_HIP]["y"]) / 2
        # Use nose (0) as head proxy
        head_y = lm[0]["y"]
        total += abs(hip_y - head_y)
        count += 1
    if count == 0:
        return height_cm
    avg_norm_height = total / count
    if avg_norm_height <= 0:
        return height_cm
    return height_cm / avg_norm_height


def _detect_foot_strikes(pose_frames):
    """Local minima in ankle y (image y increases downward) = foot strike."""
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

    def local_min_indices(ys, radius=3):
        out = []
        for i in range(radius, len(ys) - radius):
            if ys[i] is None:
                continue
            if all(ys[i] <= ys[j] for j in range(i - radius, i + radius + 1) if ys[j] is not None):
                out.append(i)
        return out

    left = local_min_indices(left_ys)
    right = local_min_indices(right_ys)
    return left, right


def _build_strides(pose_frames, strikes_left, strikes_right, scale, fps, height_cm):
    """One stride = left foot strike to next left foot strike."""
    strides = []
    for k in range(len(strikes_left) - 1):
        start_frame = strikes_left[k]
        end_frame = strikes_left[k + 1]
        stride_frames = [p for p in pose_frames if start_frame <= p["frame_idx"] < end_frame]
        if not stride_frames:
            continue
        d = _metrics_for_stride(stride_frames, start_frame, end_frame, scale, fps, height_cm)
        d["stride_num"] = k + 1
        d["start_frame"] = start_frame
        d["end_frame"] = end_frame
        strides.append(d)
    return strides


def _metrics_for_stride(stride_frames, start_frame, end_frame, scale, fps, height_cm):
    duration_sec = (end_frame - start_frame) / fps if fps else 0
    steps_per_min = (2 * 60 / duration_sec) if duration_sec > 0 else 0  # 2 steps per stride

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
    knee_angle = _knee_angle_at_strike(strike_frame, left=True)
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
    """Horizontal distance ankle to hip center; positive = foot ahead (overstride)."""
    if frame_data is None or frame_data.get("landmarks") is None:
        return None
    lm = frame_data["landmarks"]
    hip_x = (lm[LEFT_HIP]["x"] + lm[RIGHT_HIP]["x"]) / 2
    ankle_x = lm[LEFT_ANKLE]["x"]
    dx = ankle_x - hip_x
    return abs(dx) * scale if scale else None


def _trunk_lean_degrees(frame_data):
    """Trunk (shoulder-hip line) angle from vertical; forward = positive."""
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

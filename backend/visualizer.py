"""
Produce annotated video frames from pose data and results.
"""

import numpy as np

from backend.heuristics import (
    CADENCE_MIN_SPM,
    KNEE_FLEXION_MIN_DEG,
    OVERSTRIDE_CM_THRESHOLD,
    TRUNK_LEAN_MAX_DEG,
    VERTICAL_OSC_MAX_CM,
)
from backend.pose_extractor import (
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_KNEE,
    RIGHT_KNEE,
    LEFT_ANKLE,
    RIGHT_ANKLE,
)

FLAG_JOINTS = {
    "overstriding": [LEFT_ANKLE, RIGHT_ANKLE, LEFT_HIP, RIGHT_HIP],
    "knee_flexion_at_strike": [LEFT_KNEE, RIGHT_KNEE],
    "trunk_lean": [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP],
    "vertical_oscillation": [LEFT_HIP, RIGHT_HIP],
    "cadence": [LEFT_HIP, RIGHT_HIP, LEFT_ANKLE, RIGHT_ANKLE],
}

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (17, 19), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28),
]


def build_frame_to_stride_flags(strides, flags):
    flagged_metrics = {f["metric"] for f in flags}
    frame_flags = {}
    for s in strides:
        start = s.get("start_frame", 0)
        end = s.get("end_frame", start + 1)
        stride_flagged = set()
        if "cadence" in flagged_metrics and s.get("cadence") is not None:
            if s["cadence"] < CADENCE_MIN_SPM:
                stride_flagged.add("cadence")
        if "vertical_oscillation" in flagged_metrics and s.get("vertical_osc_cm") is not None:
            if s["vertical_osc_cm"] > VERTICAL_OSC_MAX_CM:
                stride_flagged.add("vertical_oscillation")
        if "knee_flexion_at_strike" in flagged_metrics and s.get("knee_angle_strike_deg") is not None:
            if s["knee_angle_strike_deg"] < KNEE_FLEXION_MIN_DEG:
                stride_flagged.add("knee_flexion_at_strike")
        if "overstriding" in flagged_metrics and s.get("foot_strike_position_cm") is not None:
            if s["foot_strike_position_cm"] > OVERSTRIDE_CM_THRESHOLD:
                stride_flagged.add("overstriding")
        if "trunk_lean" in flagged_metrics and s.get("trunk_lean_deg") is not None:
            if s["trunk_lean_deg"] > TRUNK_LEAN_MAX_DEG:
                stride_flagged.add("trunk_lean")
        for fi in range(start, end):
            frame_flags[fi] = stride_flagged
    return frame_flags


def get_flagged_joint_set(flagged_metrics):
    out = set()
    for m in flagged_metrics:
        out.update(FLAG_JOINTS.get(m, []))
    return out


def _draw_metrics_panel(img, lines, font_scale=0.9, thickness=2, padding=12, alpha=0.6):
    import cv2
    font = cv2.FONT_HERSHEY_SIMPLEX
    (_, line_h), _ = cv2.getTextSize("Ay", font, font_scale, thickness)
    line_spacing = int(line_h * 1.3)
    max_w = 0
    for line in lines:
        (w, _), _ = cv2.getTextSize(line, font, font_scale, thickness)
        max_w = max(max_w, w)
    box_w = max_w + 2 * padding
    box_h = len(lines) * line_spacing + 2 * padding
    x1, y1 = 12, 12
    x2, y2 = x1 + box_w, y1 + box_h
    roi = img[y1:y2, x1:x2]
    overlay = np.full_like(roi, (0, 0, 0), dtype=np.uint8)
    img[y1:y2, x1:x2] = cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0)
    y0 = y1 + padding + line_h
    for line in lines:
        cv2.putText(img, line, (x1 + padding, y0), font, font_scale, (255, 255, 255), thickness)
        y0 += line_spacing


def generate_annotated_frames(frames, pose_frames, results):
    import cv2
    strides = results.get("strides", [])
    flags = results.get("flags", [])
    summary = results.get("summary", {})
    frame_flags = build_frame_to_stride_flags(strides, flags)
    pose_by_idx = {p["frame_idx"]: p for p in pose_frames}

    out = []
    for i, frame in enumerate(frames):
        if frame is None:
            continue
        img = frame.copy()
        h, w = img.shape[:2]
        pose = pose_by_idx.get(i)
        flagged_joints = get_flagged_joint_set(frame_flags.get(i, set()))

        if pose and pose.get("landmarks"):
            lm = pose["landmarks"]
            pts = [(int(l["x"] * w), int(l["y"] * h)) for l in lm]
            for (a, b) in POSE_CONNECTIONS:
                if a < len(pts) and b < len(pts) and pts[a] and pts[b]:
                    cv2.line(img, pts[a], pts[b], (0, 255, 0), 2)
            for j, pt in enumerate(pts):
                if j in flagged_joints:
                    cv2.circle(img, pt, 6, (0, 0, 255), -1)
                else:
                    cv2.circle(img, pt, 4, (0, 255, 0), -1)

        stride_at_frame = _stride_at_frame(i, strides)
        if stride_at_frame:
            cad = stride_at_frame.get("cadence", "")
            osc = stride_at_frame.get("vertical_osc_cm", "")
            knee = stride_at_frame.get("knee_angle_strike_deg", "")
            lean = stride_at_frame.get("trunk_lean_deg", "")
        else:
            cad = summary.get("cadence_avg", "")
            osc = summary.get("vertical_osc_avg_cm", "")
            knee = summary.get("knee_angle_strike_avg_deg", "")
            lean = summary.get("trunk_lean_avg_deg", "")
        lines = [
            f"Cadence: {cad} spm",
            f"Vert osc: {osc} cm",
            f"Knee @ strike: {knee} deg",
            f"Trunk lean: {lean} deg",
        ]
        _draw_metrics_panel(img, lines)
        out.append(img)
    return out


def _stride_at_frame(frame_idx, strides):
    for s in strides:
        if s.get("start_frame", 0) <= frame_idx < s.get("end_frame", 0):
            return s
    return None

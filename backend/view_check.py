"""
Which way was the camera pointing? Classifies a clip as side-on, frontal
(filmed from behind or in front), or diagonal, from the pose landmarks the
pipelines already extract. Pure function, no I/O.

Signal: apparent shoulder width divided by torso length (shoulder midpoint to
hip midpoint). From the side the shoulders nearly overlap (ratio ~0-0.25);
from behind or in front they're at full width (ratio ~0.7-0.9, since
shoulder width is roughly 0.8x torso length). A diagonal camera lands in
between: at 45 degrees the ratio is ~0.55. Both pipelines letterbox frames to
a square before pose extraction, so x and y units are comparable.

Used to catch a clip uploaded to the wrong slot: a rear clip in the side slot
produced confident but meaningless knee-drive and trunk-lean numbers (knee
flexion and forward lean are invisible from behind). Thresholds are
PROVISIONAL, set from body proportions rather than tuned on labelled clips;
only the clear-cut ends reject anything, the middle band is recorded only.
"""

import math
import statistics
from dataclasses import dataclass

LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24

# Below this the clip is side-on (shoulders within ~22 deg of overlapping).
SIDE_MAX_RATIO = 0.30
# Above this the clip is frontal (camera within ~40 deg of straight behind/in front).
FRONTAL_MIN_RATIO = 0.60
# Fewer usable frames than this and we don't guess.
MIN_FRAMES = 15
_VIS_THRESHOLD = 0.5


@dataclass(frozen=True)
class ViewCheck:
    view: str  # "side" | "diagonal" | "frontal" | "unknown"
    shoulder_ratio: float | None
    frames_used: int

    def as_dict(self) -> dict:
        return {
            "view": self.view,
            "shoulder_ratio": round(self.shoulder_ratio, 3) if self.shoulder_ratio is not None else None,
            "frames_used": self.frames_used,
        }


def _frame_ratio(lm) -> float | None:
    idxs = (LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP)
    if any(lm[i].get("visibility", 1.0) < _VIS_THRESHOLD for i in idxs):
        return None
    ls, rs, lh, rh = (lm[i] for i in idxs)
    shoulder_w = math.hypot(ls["x"] - rs["x"], ls["y"] - rs["y"])
    mid_sx, mid_sy = (ls["x"] + rs["x"]) / 2, (ls["y"] + rs["y"]) / 2
    mid_hx, mid_hy = (lh["x"] + rh["x"]) / 2, (lh["y"] + rh["y"]) / 2
    torso = math.hypot(mid_sx - mid_hx, mid_sy - mid_hy)
    if torso < 1e-3:
        return None
    return shoulder_w / torso


def classify_view(pose_frames) -> ViewCheck:
    ratios = [
        r for p in pose_frames
        if (lm := p.get("landmarks")) and (r := _frame_ratio(lm)) is not None
    ]
    if len(ratios) < MIN_FRAMES:
        return ViewCheck("unknown", None, len(ratios))
    ratio = statistics.median(ratios)
    if ratio < SIDE_MAX_RATIO:
        view = "side"
    elif ratio > FRONTAL_MIN_RATIO:
        view = "frontal"
    else:
        view = "diagonal"
    return ViewCheck(view, ratio, len(ratios))


# Shoulder width / torso length seen straight from behind or in front (see the
# module docstring); the ratio falls off as sin(angle off the runner's line).
_FRONTAL_RATIO = 0.8


def degrees_off_side_on(ratio: float) -> float:
    """Rough camera angle away from a true side-on view, from shoulder_ratio:
    0 = side-on, 90 = straight behind / in front."""
    return math.degrees(math.asin(min(1.0, max(0.0, ratio / _FRONTAL_RATIO))))


def side_capture_notes(view: ViewCheck) -> list[dict]:
    """Filming tips for a SIDE clip, same shape as
    rear_confidence.capture_notes. A diagonal camera isn't rejected (the
    metrics still run) but foreshortens knee drive, trunk lean and foot
    strike, so the runner is told how far off it was."""
    if view.view != "diagonal" or view.shoulder_ratio is None:
        return []
    deg = int(round(degrees_off_side_on(view.shoulder_ratio) / 5.0) * 5)
    return [{
        "code": "camera_angle",
        "message": (
            f"The camera looks about {deg}° off side-on. Knee drive, lean and foot strike "
            "read best with the camera square to your running direction, at 90°."
        ),
    }]

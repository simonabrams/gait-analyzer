"""Synthetic rear-view pose frames for testing backend.rear_metrics. No file I/O.

Builds a runner seen from behind whose true hip drop / knee valgus /
pronation are chosen by the caller, so tests assert against known ground truth
rather than against the implementation. Left leg is on the image-left (x=0.45),
right on the image-right (x=0.55), matching a real rear view.
"""
import math

FPS = 30.0
CYCLE_FRAMES = 21  # 0.7 s stride ~ 171 spm at 30 fps

_GROUND_Y = 0.90
_SWING_LIFT = 0.15
_STANCE_FRAC = 0.35
_HIP_WIDTH = 0.10
_KNEE_Y = 0.68
_HIP_BASE_Y = 0.50
_HEEL_DROP = 0.02


def _lm(x=0.5, y=0.5, vis=1.0):
    return {"x": x, "y": y, "z": 0.0, "visibility": vis}


def _ankle_y(phase, drift=0.0):
    """Ankle height (image y) over one gait cycle: stance plateau at ground
    (with a slight peak at mid-stance so the strike detector has a maximum to
    lock onto), then a swing arc back up."""
    if phase < _STANCE_FRAC:
        y = _GROUND_Y - 0.001 * abs(phase - _STANCE_FRAC / 2)
    else:
        y = _GROUND_Y - _SWING_LIFT * math.sin(math.pi * (phase - _STANCE_FRAC) / (1 - _STANCE_FRAC))
    return y + drift


def _bump(d, half_width=0.35):
    return max(0.0, math.cos(math.pi * d / (2 * half_width))) if abs(d) < half_width else 0.0


def make_rear_frames(
    n_frames=360,
    hip_drop_left=6.0,
    hip_drop_right=6.0,
    valgus_left=8.0,
    valgus_right=8.0,
    pronation_left=4.0,
    pronation_right=4.0,
    start_phase=0.0,
    ankle_drift_per_frame=0.0,
    visibility=1.0,
):
    """Frames whose left-leg gait cycle repeats every CYCLE_FRAMES and whose
    right leg is half a cycle behind. `start_phase` shifts where in the cycle
    the clip begins (rear and side videos start at arbitrary points)."""
    frames = []
    for i in range(n_frames):
        drift = ankle_drift_per_frame * i
        lphase = ((i / CYCLE_FRAMES) + start_phase) % 1.0
        rphase = (lphase + 0.5) % 1.0

        # Pelvic tilt: peaks (right hip low) at left mid-stance, (left hip low) at right mid-stance.
        mid = _STANCE_FRAC / 2
        tilt_deg = hip_drop_left * _bump(lphase - mid) - hip_drop_right * _bump(rphase - mid)
        dy = math.tan(math.radians(tilt_deg)) * _HIP_WIDTH

        lm = [_lm(vis=visibility) for _ in range(33)]
        lm[0] = _lm(0.5, 0.20, visibility)
        lm[23] = _lm(0.45, _HIP_BASE_Y - dy / 2, visibility)  # left hip
        lm[24] = _lm(0.55, _HIP_BASE_Y + dy / 2, visibility)  # right hip

        for leg, phase, valgus, pron, x0, medial in (
            ("left", lphase, valgus_left, pronation_left, 0.45, 1.0),
            ("right", rphase, valgus_right, pronation_right, 0.55, -1.0),
        ):
            hip_i, knee_i, ankle_i, heel_i = (23, 25, 27, 29) if leg == "left" else (24, 26, 28, 30)
            ankle_y = _ankle_y(phase, drift)
            # Knee offset (toward the midline for valgus) that yields ~`valgus` degrees
            # between the hip->knee and knee->ankle segments (ankle straight below hip).
            thigh_len = _KNEE_Y - _HIP_BASE_Y
            off = medial * thigh_len * math.tan(math.radians(valgus / 2.0))
            lm[knee_i] = _lm(x0 + off, _KNEE_Y, visibility)
            lm[ankle_i] = _lm(x0, ankle_y, visibility)
            # Pronation: heel displaced laterally (away from midline) relative to the ankle.
            lm[heel_i] = _lm(x0 - medial * _HEEL_DROP * math.tan(math.radians(pron)), ankle_y + _HEEL_DROP, visibility)

        frames.append({"frame_idx": i, "timestamp_ms": i * 1000.0 / FPS, "landmarks": lm})
    return frames


def swap_left_right(frames):
    """What BlazePose does when it mislabels a runner seen from behind: every
    left landmark carries the right one's data and vice versa."""
    pairs = [(23, 24), (25, 26), (27, 28), (29, 30), (31, 32)]
    out = []
    for p in frames:
        lm = list(p["landmarks"])
        for a, b in pairs:
            lm[a], lm[b] = lm[b], lm[a]
        out.append({**p, "landmarks": lm})
    return out

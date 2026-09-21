"""
Compute frontal-plane gait metrics from REAR-view pose landmark data. Pure
functions: accept a landmark series + fps, return the `rear_view` object of the
results JSON (see backend/results_schema.py and backend/schema/results.schema.json).
No file I/O.

Independent of the side-view pipeline by design: the rear video is a separate
recording, so nothing here is synchronised or frame-matched with the side
video. Gait cycles are segmented from the rear video's own ankle signal and
every metric is expressed as a function of % of the gait cycle (0% = initial
contact of that leg, 100% = that leg's next initial contact), never raw time.

Conventions (mirrors metrics.py — MediaPipe landmark dicts, normalised image
coords with y growing downward, median aggregation after outlier rejection):
- Seen from behind, the runner's left leg is on the image-left. Frames are
  normalised so landmark "left" is always that leg (see _normalise_orientation).
- Angles are computed straight from normalised (x, y), which treats one unit of
  x and of y as the same length. That holds because the pipeline letterboxes
  frames to a square before pose extraction (job_runner._resize_and_letterbox,
  which the rear runner reuses) — feed this module un-letterboxed landmarks from
  a non-square video and every angle here is skewed by the aspect ratio.
- Positive hip_drop   = the swing-side hip is lower than the stance-side hip.
- Positive pronation  = heel everted (ankle collapsing medially over the heel).
- Positive knee_valgus = knee medial to the hip-ankle line.
"""

import math
import statistics
from datetime import datetime, timezone

from backend import rear_confidence as rc

# Reused (not re-implemented) so the rear view detects strides the same way the
# side view does; they only depend on ankle landmarks so they work from any view.
from backend.metrics import (
    _STRIDE_MAX_SEC,
    _STRIDE_MIN_SEC,
    _VIS_THRESHOLD,
    _detect_foot_strikes,
    _filter_outlier_strides,
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_KNEE,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_KNEE,
)

LEFT_HEEL, RIGHT_HEEL = 29, 30
LEFT_FOOT_INDEX, RIGHT_FOOT_INDEX = 31, 32

_LEG_LANDMARKS = {
    "left": {"hip": LEFT_HIP, "knee": LEFT_KNEE, "ankle": LEFT_ANKLE, "heel": LEFT_HEEL},
    "right": {"hip": RIGHT_HIP, "knee": RIGHT_KNEE, "ankle": RIGHT_ANKLE, "heel": RIGHT_HEEL},
}
# +1: this leg's medial side is image-right (left leg seen from behind); -1: image-left.
_MEDIAL_DIR = {"left": 1.0, "right": -1.0}
_LEG_LANDMARK_PAIRS = [
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_KNEE, RIGHT_KNEE),
    (LEFT_ANKLE, RIGHT_ANKLE),
    (LEFT_HEEL, RIGHT_HEEL),
    (LEFT_FOOT_INDEX, RIGHT_FOOT_INDEX),
]

# Hips closer than this in x (normalised) can't vote on left/right ordering
# (pelvis rotated edge-on to the camera).
_MIN_HIP_SEPARATION = 0.005

# Stance = contiguous run around a foot strike where the ankle stays within this
# fraction of the local ground-to-swing ankle-height range of its ground level.
# Per-cycle (local) so a runner drifting away from the camera (overground)
# doesn't move the threshold out from under later strides.
_STANCE_PLATEAU_FRAC = 0.25
# Stance as % of the gait cycle; outside this is a mis-segmented cycle, not running.
_STANCE_PCT_RANGE = (20.0, 60.0)

_CURVE_STEP_PCT = 5
_CURVE_POINTS = 100 // _CURVE_STEP_PCT + 1  # 21 samples: 0, 5, ..., 100 %
# A curve point is only reported if at least this fraction of usable cycles has
# a value there.
_CURVE_MIN_COVERAGE = 0.5

METRICS = ("hip_drop", "pronation", "knee_valgus")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def compute_rear_metrics(pose_frames, fps, video_file=""):
    if not pose_frames or not fps or fps <= 0:
        return _empty_rear_view(video_file, "no_frames", fps, 0, 0.0)

    frames, lr_consistency, swapped = _normalise_orientation(pose_frames)
    if not any(p.get("landmarks") for p in frames):
        return _empty_rear_view(video_file, "no_pose_detected", fps, len(pose_frames), lr_consistency)

    sig = _frame_signals(frames)
    strikes = dict(zip(("left", "right"), _detect_foot_strikes(frames, fps=fps)))

    legs, leg_cycles, all_cycle_counts = {}, {}, {}
    for leg in ("left", "right"):
        cycles, detected = _segment_leg_cycles(frames, strikes[leg], _LEG_LANDMARKS[leg]["ankle"], fps)
        usable = _filter_outlier_strides(cycles) if cycles else []
        for c in usable:
            c.update(_cycle_metrics(leg, c, sig))
        leg_cycles[leg] = usable
        all_cycle_counts[leg] = len(usable)
        legs[leg] = {"cycles_detected": detected, "cycles_usable": len(usable)}

    gate = rc.evaluate_gate(all_cycle_counts, lr_consistency)

    medians = {m: {} for m in METRICS}
    for leg in ("left", "right"):
        usable = leg_cycles[leg]
        if leg not in gate.reportable_legs:
            legs[leg].update(_unavailable_leg("insufficient_cycles"))
            continue
        stance = statistics.median(c["stance_pct"] for c in usable)
        midstance = statistics.median(c["midstance_pct"] for c in usable)
        legs[leg]["stance_pct"] = round(stance, 1)
        legs[leg]["midstance_pct"] = round(midstance, 1)
        for metric in METRICS:
            window = [midstance, midstance] if metric == "hip_drop" else [0.0, midstance]
            obj, median = _metric_object(
                metric,
                [c[metric] for c in usable],
                vis=_mean_visibility(frames, leg, metric),
                fps=fps,
                lr=lr_consistency,
                window_pct=[round(w, 1) for w in window],
            )
            legs[leg][metric] = obj
            if median is not None:
                medians[metric][leg] = median

    for leg in ("left", "right"):
        legs[leg]["reportable"] = leg in gate.reportable_legs

    symmetry = _symmetry(legs, medians) if gate.status != "insufficient_data" else _unavailable_symmetry()
    curves = _curves(leg_cycles, gate.reportable_legs, sig) if gate.reportable_legs else None

    return {
        "status": gate.status,
        "meta": _meta(video_file, fps, len(pose_frames), lr_consistency, swapped),
        "confidence_gate": _gate_dict(gate),
        "legs": legs,
        "symmetry": symmetry,
        "curves": curves,
    }


# ---------------------------------------------------------------------------
# Output scaffolding
# ---------------------------------------------------------------------------
def _meta(video_file, fps, num_frames, lr_consistency, swapped):
    return {
        "video_file": video_file,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "fps": fps,
        "num_frames": num_frames,
        "cycle_normalisation": "percent_gait_cycle",
        "synchronized_with_side_view": False,
        "note": rc.REAR_UNSYNCHRONISED_NOTE,
        "left_right_consistency": round(lr_consistency, 3),
        "left_right_labels_swapped": swapped,
    }


def _gate_dict(gate):
    return {
        "status": gate.status,
        "reason": gate.reason,
        "user_message": gate.user_message,
        "usable_cycles": gate.usable_cycles,
        "left_right_consistency": round(gate.lr_consistency, 3),
    }


def _unavailable_leg(reason):
    out = {}
    for metric in METRICS:
        out[metric] = {"available": False, "reason": reason}
    return out


def _unavailable_symmetry():
    return {"available": False, "reason": "insufficient_data"}


def _empty_rear_view(video_file, reason, fps, num_frames, lr_consistency):
    """No usable rear-view data at all — the rear analogue of metrics._empty_results.
    Still a well-formed rear_view object so consumers never special-case shape."""
    gate = rc.RearGateResult(
        status="insufficient_data",
        reason=reason,
        user_message=(
            "We couldn't find a runner in the rear-view clip. Try filming "
            "directly from behind with your full body in frame and good lighting."
        ),
        reportable_legs=(),
        usable_cycles={"left": 0, "right": 0},
        lr_consistency=lr_consistency,
    )
    return {
        "status": "insufficient_data",
        "meta": _meta(video_file, fps, num_frames, lr_consistency, False),
        "confidence_gate": _gate_dict(gate),
        "legs": {
            leg: {"cycles_detected": 0, "cycles_usable": 0, "reportable": False, **_unavailable_leg(reason)}
            for leg in ("left", "right")
        },
        "symmetry": _unavailable_symmetry(),
        "curves": None,
    }


# ---------------------------------------------------------------------------
# Orientation
# ---------------------------------------------------------------------------
def _copy_landmarks(lm):
    return dict(lm) if isinstance(lm, dict) else list(lm)


def _swap_lr(lm):
    out = _copy_landmarks(lm)
    for a, b in _LEG_LANDMARK_PAIRS:
        out[a], out[b] = lm[b], lm[a]
    return out


def _normalise_orientation(pose_frames):
    """Return (frames, lr_consistency, swapped).

    Seen from behind, the runner's left hip is on the image-left, so
    "left hip x < right hip x" is the expected ordering. BlazePose is trained
    mostly on front-facing people and is known to swap left/right on subjects
    facing away, either for the whole clip or for stray frames. Attributing
    one leg's numbers to the other would be worse than reporting nothing, so:
      - the majority ordering across the clip decides the labels (if the
        model's "left" is consistently on the image-right, swap all labels);
      - frames that contradict the majority are dropped (landmarks -> None);
      - lr_consistency (majority share) feeds the confidence gate.
    Frames whose hips can't vote (low visibility / edge-on pelvis) are kept and
    follow the majority decision.
    """
    votes = []
    for p in pose_frames:
        lm = p.get("landmarks")
        if (
            lm is None
            or lm[LEFT_HIP].get("visibility", 1.0) < _VIS_THRESHOLD
            or lm[RIGHT_HIP].get("visibility", 1.0) < _VIS_THRESHOLD
        ):
            votes.append(0)
            continue
        dx = lm[LEFT_HIP]["x"] - lm[RIGHT_HIP]["x"]
        votes.append(0 if abs(dx) < _MIN_HIP_SEPARATION else (1 if dx > 0 else -1))

    positive, negative = votes.count(1), votes.count(-1)
    total = positive + negative
    if total == 0:
        return [dict(p) for p in pose_frames], 0.0, False

    swapped = positive > negative
    keep = 1 if swapped else -1
    frames = []
    for p, v in zip(pose_frames, votes):
        lm = p.get("landmarks")
        if lm is None or (v != 0 and v != keep):
            frames.append({**p, "landmarks": None})
        else:
            frames.append({**p, "landmarks": _swap_lr(lm) if swapped else lm})
    return frames, max(positive, negative) / total, swapped


# ---------------------------------------------------------------------------
# Per-frame frontal-plane signals (pure; None when landmarks aren't trustworthy)
# ---------------------------------------------------------------------------
def _visible(lm, *idxs):
    return all(lm[i].get("visibility", 1.0) >= _VIS_THRESHOLD for i in idxs)


def pelvic_tilt_deg(lm):
    """Angle of the hip line above image-horizontal, in degrees; positive when
    the RIGHT hip is lower than the left (image y grows downward). Derived from
    the vertical delta between the hips normalised by hip width, so it's
    independent of how big the runner is in frame. Camera roll is NOT removed —
    a level camera is part of the filming guidance — and adds an equal and
    opposite offset to each leg's hip drop."""
    if not _visible(lm, LEFT_HIP, RIGHT_HIP):
        return None
    dx = abs(lm[RIGHT_HIP]["x"] - lm[LEFT_HIP]["x"])
    if dx < _MIN_HIP_SEPARATION:
        return None
    return math.degrees(math.atan2(lm[RIGHT_HIP]["y"] - lm[LEFT_HIP]["y"], dx))


def hip_drop_from_tilt(leg, tilt):
    """Hip drop for `leg` while it is the stance leg: the contralateral hip
    dropping below the stance hip. Left stance -> right hip low -> positive tilt."""
    if tilt is None:
        return None
    return tilt if leg == "left" else -tilt


def pronation_deg(lm, leg):
    """Rearfoot pronation(+) / supination(-) proxy: angle of the ankle->heel
    vector from vertical. Pronation = heel displaced laterally relative to the
    ankle (ankle collapsing medially). Deliberately a proxy: the vector is only
    a few pixels long from behind, so it's noisy and is capped at low
    confidence (rear_confidence.TIER_CEILING)."""
    idx = _LEG_LANDMARKS[leg]
    if not _visible(lm, idx["ankle"], idx["heel"]):
        return None
    dy = lm[idx["heel"]]["y"] - lm[idx["ankle"]]["y"]
    if dy <= 0:  # heel above the ankle: landmark noise, not a foot
        return None
    lateral_shift = -_MEDIAL_DIR[leg] * (lm[idx["heel"]]["x"] - lm[idx["ankle"]]["x"])
    return math.degrees(math.atan2(lateral_shift, dy))


def knee_valgus_deg(lm, leg):
    """Frontal-plane knee valgus(+) / varus(-): how far the hip->knee and
    knee->ankle segments bend away from a straight leg, signed positive when
    the knee sits medial to the hip-ankle line. Uses both segments (not just the
    knee->ankle line vs vertical) so stance width and leg abduction aren't
    mistaken for valgus."""
    idx = _LEG_LANDMARKS[leg]
    if not _visible(lm, idx["hip"], idx["knee"], idx["ankle"]):
        return None
    tx = lm[idx["knee"]]["x"] - lm[idx["hip"]]["x"]
    ty = lm[idx["knee"]]["y"] - lm[idx["hip"]]["y"]
    sx = lm[idx["ankle"]]["x"] - lm[idx["knee"]]["x"]
    sy = lm[idx["ankle"]]["y"] - lm[idx["knee"]]["y"]
    if ty <= 0 or sy <= 0:  # segments must point down the image
        return None
    thigh = math.degrees(math.atan2(tx, ty))
    shank = math.degrees(math.atan2(sx, sy))
    return _MEDIAL_DIR[leg] * (thigh - shank)


def _frame_signals(frames):
    tilt, pron, valg = [], {"left": [], "right": []}, {"left": [], "right": []}
    for p in frames:
        lm = p.get("landmarks")
        tilt.append(pelvic_tilt_deg(lm) if lm else None)
        for leg in ("left", "right"):
            pron[leg].append(pronation_deg(lm, leg) if lm else None)
            valg[leg].append(knee_valgus_deg(lm, leg) if lm else None)
    return {"tilt": tilt, "pronation": pron, "knee_valgus": valg}


def _mean_visibility(frames, leg, metric):
    idx = _LEG_LANDMARKS[leg]
    if metric == "hip_drop":
        used = [LEFT_HIP, RIGHT_HIP]
    elif metric == "pronation":
        used = [idx["ankle"], idx["heel"]]
    else:
        used = [idx["hip"], idx["knee"], idx["ankle"]]
    vals = [
        lm[i].get("visibility", 1.0)
        for p in frames
        if (lm := p.get("landmarks"))
        for i in used
    ]
    return sum(vals) / len(vals) if vals else 0.0


# ---------------------------------------------------------------------------
# Gait-cycle segmentation (per leg, from the rear video's own ankle signal)
# ---------------------------------------------------------------------------
def _fill_gaps(values):
    """Linear interpolation over None gaps; edges take the nearest value."""
    known = [i for i, v in enumerate(values) if v is not None]
    if not known:
        return None
    out = list(values)
    for i in range(known[0]):
        out[i] = values[known[0]]
    for i in range(known[-1] + 1, len(values)):
        out[i] = values[known[-1]]
    for a, b in zip(known, known[1:]):
        for i in range(a + 1, b):
            t = (i - a) / (b - a)
            out[i] = values[a] + t * (values[b] - values[a])
    return out


def _duration_sec(frames, start, end, fps):
    t0, t1 = frames[start].get("timestamp_ms"), frames[end].get("timestamp_ms")
    if t0 is not None and t1 is not None:
        return (t1 - t0) / 1000.0
    return (end - start) / fps


def _segment_leg_cycles(frames, strikes, ankle_idx, fps):
    """Turn one leg's foot strikes into gait cycles bounded by initial
    contacts. Returns (valid_cycles, n_detected_candidate_cycles).

    Each strike from _detect_foot_strikes is the ankle's lowest point, which
    lands somewhere along the stance plateau, not necessarily on first contact.
    So each strike is expanded to the plateau around it (initial contact = its
    first frame, toe-off = its last) and cycles run IC -> next IC. Positions
    are indices into `frames`.
    """
    raw = []
    for p in frames:
        lm = p.get("landmarks")
        raw.append(lm[ankle_idx]["y"] if lm and _visible(lm, ankle_idx) else None)
    y = _fill_gaps(raw)
    if y is None or len(strikes) < 2:
        return [], 0

    n = len(y)
    max_span = max(2, int(_STRIDE_MAX_SEC * fps))
    landings = []  # (ic, toe_off) per strike, or None
    for k, pk in enumerate(strikes):
        lo = strikes[k - 1] if k > 0 else max(0, pk - max_span)
        hi = strikes[k + 1] if k + 1 < len(strikes) else min(n - 1, pk + max_span)
        ymax, ymin = y[pk], min(y[lo:hi + 1])
        if ymax - ymin <= 0:
            landings.append(None)
            continue
        thr = ymax - _STANCE_PLATEAU_FRAC * (ymax - ymin)
        ic = pk
        while ic - 1 >= lo and y[ic - 1] >= thr:
            ic -= 1
        to = pk
        while to + 1 <= hi and y[to + 1] >= thr:
            to += 1
        landings.append((ic, to))

    cycles, detected = [], 0
    for cur, nxt in zip(landings, landings[1:]):
        if cur is None or nxt is None:
            continue
        detected += 1
        ic, to = cur
        end = nxt[0]
        length = end - ic
        if length <= 0 or to >= end:
            continue
        duration = _duration_sec(frames, ic, end, fps)
        if not (_STRIDE_MIN_SEC <= duration <= _STRIDE_MAX_SEC):
            continue
        stance_pct = (to - ic + 1) / length * 100.0
        if not (_STANCE_PCT_RANGE[0] <= stance_pct <= _STANCE_PCT_RANGE[1]):
            continue
        cycles.append({
            "ic": ic,
            "to": to,
            "end": end,
            "duration_sec": round(duration, 3),
            "stance_pct": stance_pct,
            "midstance_pct": (to - ic) / 2.0 / length * 100.0,
        })
    return cycles, detected


# ---------------------------------------------------------------------------
# Per-cycle metrics
# ---------------------------------------------------------------------------
def _median_or_none(values):
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def _mean_or_none(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _cycle_metrics(leg, cycle, sig):
    """Metrics for one gait cycle of `leg`, each computed at its own point in
    the cycle: hip drop AT mid-stance (mean of the frames within +/-1 of it, so
    one blurry frame doesn't decide it — same idea as metrics._knee_angle_window),
    pronation and knee valgus from initial contact THROUGH mid-stance (median)."""
    ic, mid = cycle["ic"], cycle["ic"] + (cycle["to"] - cycle["ic"]) / 2.0
    near_mid = range(max(0, int(math.ceil(mid - 1.0))), min(len(sig["tilt"]) - 1, int(math.floor(mid + 1.0))) + 1)
    window = range(ic, int(math.floor(mid)) + 1)
    return {
        "hip_drop": _mean_or_none([hip_drop_from_tilt(leg, sig["tilt"][p]) for p in near_mid]),
        "pronation": _median_or_none([sig["pronation"][leg][p] for p in window]),
        "knee_valgus": _median_or_none([sig["knee_valgus"][leg][p] for p in window]),
    }


def _metric_object(metric, values, vis, fps, lr, window_pct):
    """Aggregate one metric across a leg's usable cycles -> (json object, raw
    median or None). Median, not mean, for the same reason as
    metrics._compute_summary: one bad cycle shouldn't drag the value."""
    vals = [v for v in values if v is not None]
    if len(vals) < rc.MIN_CYCLES_FOR_REPORT:
        return {"available": False, "reason": "insufficient_data"}, None
    median = statistics.median(vals)
    if not rc.within_bounds(metric, median):
        return {"available": False, "reason": "implausible"}, None
    spread = statistics.median(abs(v - median) for v in vals)
    score = rc.confidence_score(metric, len(vals), vis, fps, lr, spread)
    shown = rc.display_value(metric, median)
    return {
        "available": True,
        "value_deg": shown,
        "pattern": rc.pattern_for(metric, shown),
        "window_pct": window_pct,
        "cycles_used": len(vals),
        "error_margin_deg": rc.ERROR_MARGIN_DEG[metric],
        "confidence": {"score": score, "tier": rc.tier_for(metric, score)},
        "disclaimer": rc.DISCLAIMERS[metric],
    }, median


# ---------------------------------------------------------------------------
# Symmetry
# ---------------------------------------------------------------------------
def _symmetry(legs, medians):
    """Left/right symmetry score (0-100, higher = more symmetric) — mean of the
    per-metric scores 100 - SI over the metrics available on BOTH legs."""
    components, tiers, scores = {}, [], []
    for metric in METRICS:
        m = medians[metric]
        if "left" not in m or "right" not in m:
            continue
        si = rc.symmetry_index(metric, m["left"], m["right"])
        components[metric] = int(round(max(0.0, 100.0 - si)))
        for leg in ("left", "right"):
            conf = legs[leg][metric]["confidence"]
            tiers.append(conf["tier"])
            scores.append(conf["score"])
    if len(components) < 2:
        return _unavailable_symmetry()
    score = int(round(sum(components.values()) / len(components)))
    weakest = min(tiers, key=rc._TIER_ORDER.index)
    return {
        "available": True,
        "score": score,
        "band": rc.symmetry_band(score),
        "components": components,
        "confidence": {"score": round(sum(scores) / len(scores), 3), "tier": weakest},
        "disclaimer": rc.DISCLAIMERS["symmetry"],
    }


# ---------------------------------------------------------------------------
# Ensemble-average curves over the gait cycle
# ---------------------------------------------------------------------------
def _resample_cycle(series, ic, end):
    """Linearly resample series[ic..end] to _CURVE_POINTS samples at 0..100 %
    of the cycle. A sample is None when either neighbouring frame is missing."""
    out = []
    for i in range(_CURVE_POINTS):
        pos = ic + (end - ic) * i / (_CURVE_POINTS - 1)
        lo, hi = int(math.floor(pos)), int(math.ceil(pos))
        a, b = series[lo], series[hi]
        if a is None or b is None:
            out.append(None)
        else:
            out.append(a + (pos - lo) * (b - a))
    return out


def _curves(leg_cycles, reportable_legs, sig):
    out = {"step_pct": _CURVE_STEP_PCT, "unit": "deg"}
    for leg in ("left", "right"):
        if leg not in reportable_legs:
            out[leg] = None
            continue
        series_by_metric = {
            "hip_drop": [hip_drop_from_tilt(leg, t) for t in sig["tilt"]],
            "pronation": sig["pronation"][leg],
            "knee_valgus": sig["knee_valgus"][leg],
        }
        curves = {}
        for metric, series in series_by_metric.items():
            per_cycle = [_resample_cycle(series, c["ic"], c["end"]) for c in leg_cycles[leg]]
            points = []
            for i in range(_CURVE_POINTS):
                vals = [c[i] for c in per_cycle if c[i] is not None]
                enough = len(vals) >= max(3, _CURVE_MIN_COVERAGE * len(per_cycle))
                points.append(round(statistics.median(vals), 1) if enough else None)
            curves[f"{metric}_deg"] = points
        out[leg] = curves
    return out

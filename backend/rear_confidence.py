"""
Confidence scoring and "how much to trust this" policy for rear-view metrics.

Mirrors backend/confidence_gate.py (pure functions, all tuning constants in
one place, nothing here does I/O) but is a separate module because the rear
view is deliberately held to a different standard than the side view:

- It NEVER blocks or fails a run. The side-view gate hard-fails the whole
  report; a rear-view problem only ever downgrades `rear_view.status` (see
  evaluate_gate) and leaves the side-view results untouched.
- Its bands are wider, and its outputs are framed as pattern/trend
  indicators, not measurements. Single-camera 2D frontal-plane knee angles
  in running agree poorly with motion capture: one study found 2D video
  overestimated knee valgus by ~26 deg, and a 2023 meta-analysis rated
  frontal-plane validity poor to moderate. That is larger than the whole
  range of "normal", so a lone angle can't be trusted; a consistent
  left/right difference or a change between sessions can be. (An earlier
  "+/-19 deg" figure here had no source and was removed.)

Every number below marked PROVISIONAL is a starting point to tune against real
rear-view clips; none of them is a validated clinical threshold.
"""
from dataclasses import dataclass

# --- Cycle-count thresholds (per leg) ---------------------------------------
# Wider (more permissive) than the side gate's 8 / 12 total strides: these are
# per-leg gait cycles, and the outputs are patterns, not precise values.
MIN_CYCLES_FOR_REPORT = 5
MIN_CYCLES_FOR_CONFIDENT = 10

# If fewer than this fraction of frames have the hips in the expected
# left/right image order for a rear view, per-leg attribution can't be trusted
# (BlazePose is known to swap left/right on subjects facing away) — report
# nothing rather than attribute one leg's numbers to the other.
MIN_LR_CONSISTENCY_FOR_REPORT = 0.75

# --- Confidence score -> tier ----------------------------------------------
# Wider bands than a 0.8/0.5 style split would suggest for the side view:
# "high" is hard to reach on purpose, and each metric has a ceiling.
TIER_HIGH_MIN = 0.75
TIER_MODERATE_MIN = 0.50
_TIER_ORDER = ("low", "moderate", "high")

# Even with perfect inputs, none of these should read "high": hip drop is the
# best-behaved of the three but still a 2D projection with unvalidated
# error; pronation is a proxy from a very short ankle-heel vector; 2D knee
# alignment can be off by 20+ deg vs. motion capture. PROVISIONAL.
TIER_CEILING = {
    "hip_drop": "moderate",
    "pronation": "low",
    "knee_valgus": "moderate",
    "step_width": "moderate",
}

# Unit each metric is reported in. step_width is a distance, expressed as % of
# the runner's own hip width (hip-joint to hip-joint) so it needs no camera
# calibration; the *_DEG tables below hold its values in those % units.
UNIT = {"hip_drop": "deg", "pronation": "deg", "knee_valgus": "deg", "step_width": "pct"}

# Cycle-to-cycle spread (median absolute deviation, deg) at which the spread
# component of the confidence score bottoms out at 0. PROVISIONAL.
SPREAD_REFERENCE_DEG = {"hip_drop": 4.0, "pronation": 6.0, "knee_valgus": 8.0, "step_width": 15.0}

# --- Error margins -----------------------------------------------------------
# All None ("unvalidated") rather than invented: a made-up +/- reads as more
# authoritative than the truth, which is that we don't have one. Knee valgus
# used to carry an unsourced 19.0. Fill these in from our own repeatability /
# accuracy study (improvement plan, Phase 4), not from a single paper.
ERROR_MARGIN_DEG = {"hip_drop": None, "pronation": None, "knee_valgus": None, "step_width": None}

# --- Plausibility bounds (deg) ----------------------------------------------
# Outside these a value is almost certainly a landmark artifact. Unlike the
# side gate (one implausible metric fails the whole report), only the
# offending metric is dropped here — rear is optional and partial patterns
# are still useful.
METRIC_BOUNDS_DEG = {
    "hip_drop": (-10.0, 30.0),
    "pronation": (-30.0, 35.0),
    "knee_valgus": (-40.0, 40.0),
    "step_width": (-60.0, 120.0),  # % of hip width
}

# --- Pattern bands (deg). PROVISIONAL and deliberately wide ------------------
# hip_drop: positive = the swing-side hip sits lower than the stance-side hip.
# Measured as the dip from initial contact to the lowest point in stance (see
# rear_metrics._cycle_metrics), so a tilted camera or a naturally uneven pelvis
# doesn't count. Lowered from 8 / 14: in 2D video studies injured runners
# averaged ~6.4 deg of contralateral pelvic drop vs ~3.7 deg in healthy ones
# (Bramah et al. 2018). Recalibrate against our own repeatability data.
HIP_DROP_ELEVATED_DEG = 6.0
HIP_DROP_PRONOUNCED_DEG = 10.0
# pronation: positive = pronation (heel everted), negative = supination.
PRONATION_NEUTRAL_DEG = 8.0
# knee_valgus: positive = valgus (knee medial), negative = varus. Wider than
# the metric's noise floor would justify on its own — the disclaimer and tier
# carry the caveat; this is only the direction of the pattern.
KNEE_VALGUS_NEUTRAL_DEG = 12.0

# --- Display rounding step (deg): coarser = less false precision -------------
# step_width: where the foot lands relative to the body's midline, % of hip
# width. 0 = on the midline; below it the foot crosses over (crossover gait,
# linked to higher shin and IT-band load). ~50 = under the hip joint.
STEP_WIDTH_CROSSOVER_PCT = 0.0
STEP_WIDTH_NARROW_PCT = 10.0

DISPLAY_STEP_DEG = {"hip_drop": 1.0, "pronation": 2.0, "knee_valgus": 5.0, "step_width": 5.0}

# --- Symmetry ----------------------------------------------------------------
# Symmetry index SI = 100 * |L - R| / max(mean(|L|, |R|), floor). The floor
# stops two near-zero values from producing a huge SI out of noise.
SYMMETRY_FLOOR_DEG = {"hip_drop": 2.0, "pronation": 3.0, "knee_valgus": 3.0, "step_width": 10.0}
SYMMETRY_BAND_SYMMETRIC_MIN = 85
SYMMETRY_BAND_MILD_MIN = 65

# --- Disclaimers -------------------------------------------------------------
# Same job as the "±~10% vs. lab-grade motion capture" / "best compared
# session-to-session" lines in the frontend's MetricCards, but emitted in the
# JSON so the copy has one source of truth (the frontend is free to override).
_SESSION_TO_SESSION = "Best used to spot side-to-side differences and changes between sessions."
DISCLAIMERS = {
    "hip_drop": (
        "How far your pelvis dips on the swing side between foot strike and the "
        "lowest point of stance, from a rear-view video. Measured from your own "
        "foot strike, so a slightly tilted camera doesn't count. " + _SESSION_TO_SESSION
    ),
    "pronation": (
        "A rough proxy from the angle of your ankle-to-heel line, which is short "
        "and hard to track from a phone camera. Treat it as a pattern, not an angle. "
        + _SESSION_TO_SESSION
    ),
    "knee_valgus": (
        "Whether your knee tracks inward or outward of the hip-to-ankle line "
        "early in stance. Knee angles from a single camera can differ a lot from "
        "lab measurements (studies report 20° or more), so treat this as a "
        "pattern, not a precise angle. " + _SESSION_TO_SESSION
    ),
    "step_width": (
        "Where your foot lands relative to the middle of your body, as a share of "
        "your hip width. Below zero means the foot crosses the midline. "
        + _SESSION_TO_SESSION
    ),
    "symmetry": (
        "Combines the rear-view patterns above, so it carries all of their "
        "uncertainty. " + _SESSION_TO_SESSION
    ),
}

REAR_UNSYNCHRONISED_NOTE = (
    "Rear-view results come from a separate recording and are not frame-matched "
    "to the side-view video; both are expressed as % of the gait cycle."
)


@dataclass
class RearGateResult:
    status: str  # "ok" | "low_confidence" | "insufficient_data"
    reason: str | None  # set when insufficient_data
    user_message: str | None
    reportable_legs: tuple[str, ...]  # legs with >= MIN_CYCLES_FOR_REPORT usable cycles
    usable_cycles: dict[str, int]
    lr_consistency: float


def evaluate_gate(usable_cycles: dict[str, int], lr_consistency: float) -> RearGateResult:
    """Decide how much of the rear-view analysis can be reported. Pure — see
    the module docstring for why this never fails the run itself."""
    reportable = tuple(
        leg for leg in ("left", "right") if usable_cycles.get(leg, 0) >= MIN_CYCLES_FOR_REPORT
    )

    if lr_consistency < MIN_LR_CONSISTENCY_FOR_REPORT:
        return RearGateResult(
            status="insufficient_data",
            reason="unreliable_left_right",
            user_message=(
                "We couldn't tell your left leg from your right in this clip, so "
                "we can't say which side any result belongs to. Try filming "
                "directly from behind with your full body in frame."
            ),
            reportable_legs=(),
            usable_cycles=dict(usable_cycles),
            lr_consistency=lr_consistency,
        )

    if not reportable:
        most = max(usable_cycles.values(), default=0)
        return RearGateResult(
            status="insufficient_data",
            reason="insufficient_cycles",
            user_message=(
                f"We only found {most} usable stride{'s' if most != 1 else ''} per leg in "
                "the rear-view clip — not enough to see a pattern. Try 10–15 "
                "seconds of steady running filmed straight from behind, camera "
                "at about hip height."
            ),
            reportable_legs=(),
            usable_cycles=dict(usable_cycles),
            lr_consistency=lr_consistency,
        )

    low = len(reportable) < 2 or any(
        usable_cycles.get(leg, 0) < MIN_CYCLES_FOR_CONFIDENT for leg in reportable
    )
    return RearGateResult(
        status="low_confidence" if low else "ok",
        reason=None,
        user_message=None,
        reportable_legs=reportable,
        usable_cycles=dict(usable_cycles),
        lr_consistency=lr_consistency,
    )


def confidence_score(
    metric: str,
    usable_cycles: int,
    mean_visibility: float,
    fps: float,
    lr_consistency: float,
    spread_deg: float,
) -> float:
    """0-1 score for one metric on one leg, in the same spirit as the side
    view's cadence_confidence (mean of fps / visibility / stride-count terms)
    plus two rear-specific terms: left/right label consistency and how much
    the metric jumps around cycle to cycle."""
    fps_score = min(fps / 60.0, 1.0) if fps and fps > 0 else 0.0
    cycle_score = min(usable_cycles / float(MIN_CYCLES_FOR_CONFIDENT), 1.0)
    vis_score = max(0.0, min(mean_visibility, 1.0))
    consistency = max(0.0, min(lr_consistency, 1.0))
    ref = SPREAD_REFERENCE_DEG[metric]
    spread_score = 1.0 - min(max(spread_deg, 0.0) / ref, 1.0)
    return round((fps_score + cycle_score + vis_score + consistency + spread_score) / 5.0, 3)


def tier_for(metric: str, score: float) -> str:
    """Score -> "low" | "moderate" | "high", capped at TIER_CEILING[metric]."""
    if score >= TIER_HIGH_MIN:
        tier = "high"
    elif score >= TIER_MODERATE_MIN:
        tier = "moderate"
    else:
        tier = "low"
    ceiling = TIER_CEILING[metric]
    if _TIER_ORDER.index(tier) > _TIER_ORDER.index(ceiling):
        return ceiling
    return tier


def within_bounds(metric: str, value: float) -> bool:
    lo, hi = METRIC_BOUNDS_DEG[metric]
    return lo <= value <= hi


def pattern_for(metric: str, value: float) -> str:
    """Coarse category for `value` (deg) — what the UI should lead with."""
    if metric == "hip_drop":
        if value >= HIP_DROP_PRONOUNCED_DEG:
            return "pronounced"
        if value >= HIP_DROP_ELEVATED_DEG:
            return "elevated"
        return "typical"
    if metric == "pronation":
        if value > PRONATION_NEUTRAL_DEG:
            return "pronation_pattern"
        if value < -PRONATION_NEUTRAL_DEG:
            return "supination_pattern"
        return "neutral"
    if metric == "knee_valgus":
        if value > KNEE_VALGUS_NEUTRAL_DEG:
            return "valgus_pattern"
        if value < -KNEE_VALGUS_NEUTRAL_DEG:
            return "varus_pattern"
        return "neutral"
    if metric == "step_width":
        if value < STEP_WIDTH_CROSSOVER_PCT:
            return "crossover"
        if value < STEP_WIDTH_NARROW_PCT:
            return "narrow"
        return "typical"
    raise ValueError(f"unknown rear-view metric: {metric}")


def display_value(metric: str, value: float) -> int:
    """Round to the metric's display step (coarser for less trustworthy metrics)."""
    step = DISPLAY_STEP_DEG[metric]
    return int(round(round(value / step) * step))


def symmetry_index(metric: str, left: float, right: float) -> float:
    """Symmetry index in percent (0 = identical). See SYMMETRY_FLOOR_DEG."""
    denom = max((abs(left) + abs(right)) / 2.0, SYMMETRY_FLOOR_DEG[metric])
    return 100.0 * abs(left - right) / denom


def symmetry_band(score: float) -> str:
    if score >= SYMMETRY_BAND_SYMMETRIC_MIN:
        return "symmetric"
    if score >= SYMMETRY_BAND_MILD_MIN:
        return "mild_asymmetry"
    return "notable_asymmetry"

"""
The single choke point for "is this run's data trustworthy enough to report."

Runs after metrics.compute_metrics() and before evaluate_heuristics() / any
output generation (annotated video overlay, dashboard PNG, and — indirectly,
since it reads results_json — the Pro PDF). A run that fails here must never
reach a coaching recommendation: this is the boundary that turns a marginal
measurement into "we couldn't measure your gait this time" instead of a
confidently-wrong number and a confidently-wrong drill.

Two outcomes below hard-fail: "ok" (report normally) and "low_confidence"
(report, but every surface should say so — see docs/trust or the frontend's
run detail page for how that's surfaced). Tune thresholds here; nothing that
calls evaluate() should hardcode a number of its own.
"""
from dataclasses import dataclass, field

# A 10-15s clip at a typical recreational cadence yields roughly 15-25
# strides (see the app's own filming guidance). Below MIN_STRIDES_FOR_REPORT
# there usually isn't enough data left, after outlier rejection, to trust
# any of the derived metrics -- hard fail rather than report from noise.
MIN_STRIDES_FOR_REPORT = 8
# 8..11 usable strides: report, but every surface must say the confidence
# is lower than usual (see item 9 in the task -- this is not a hard fail).
MIN_STRIDES_FOR_CONFIDENT = 12

# Plausibility bounds for the *aggregate* (summary) values -- a second,
# report-level check independent of the per-stride detection-time filtering
# in metrics.py (_suppress_close_peaks, _STRIDE_MIN_SEC/_STRIDE_MAX_SEC).
# Any metric outside its bound is impossible for a real running video and
# is far more likely to be a detection artifact than a genuine reading --
# hard fail rather than coach on it (confirmed with the task's requester:
# an out-of-bounds value on *any* of these hard-fails the whole report, not
# just that one metric -- a report with one metric silently missing reads
# as more trustworthy than it is).
CADENCE_BOUNDS_SPM = (120, 220)
BOUNCE_BOUNDS_CM = (2, 25)
# Knee drive is degrees of flexion from a straight leg (0 = straight, larger
# = more bend) as of metrics.py's _knee_angle_window fix -- NOT the raw
# hip-knee-ankle joint angle. Real running flexion at strike is roughly
# 10-40 deg even for aggressive form; 90 is a generous ceiling that only
# catches a detection that's clearly broken, not real variation.
KNEE_DRIVE_BOUNDS_DEG = (0, 90)
FOOT_STRIKE_BOUNDS_CM = (0, 40)
TRUNK_LEAN_BOUNDS_DEG = (0, 30)

_METRIC_BOUNDS = {
    "cadence_avg": ("cadence", CADENCE_BOUNDS_SPM),
    "vertical_osc_avg_cm": ("bounce", BOUNCE_BOUNDS_CM),
    "knee_angle_strike_avg_deg": ("knee drive", KNEE_DRIVE_BOUNDS_DEG),
    "foot_strike_position_avg_cm": ("foot strike position", FOOT_STRIKE_BOUNDS_CM),
    "trunk_lean_avg_deg": ("trunk lean", TRUNK_LEAN_BOUNDS_DEG),
}


@dataclass
class GateResult:
    hard_fail: bool
    low_confidence: bool
    reason: str | None  # only set when hard_fail
    reason_metric: str | None  # which metric/check triggered a hard fail, if any
    detected_stride_count: int
    usable_stride_count: int
    computed_cadence: float | None
    # User-facing sentence for the "couldn't measure" screen's guidance list,
    # tailored to the actual reason -- set only when hard_fail is True.
    user_message: str | None = field(default=None)


def evaluate(summary: dict) -> GateResult:
    """Decide whether `summary` (from metrics.compute_metrics) is trustworthy
    enough to report. Pure function -- no I/O, no side effects, so it's cheap
    to unit test and safe to call from anywhere in the pipeline."""
    detected = summary.get("num_strides_detected", summary.get("num_strides", 0)) or 0
    usable = summary.get("num_strides", 0) or 0
    cadence = summary.get("cadence_avg")

    if usable < MIN_STRIDES_FOR_REPORT:
        return GateResult(
            hard_fail=True,
            low_confidence=False,
            reason="insufficient_strides",
            reason_metric=None,
            detected_stride_count=detected,
            usable_stride_count=usable,
            computed_cadence=cadence,
            user_message=(
                f"We only detected {usable} usable stride"
                f"{'s' if usable != 1 else ''} in this clip — not enough to report "
                "reliable numbers. Try a longer clip (10–15 seconds of steady "
                "running) or a clearer side-on angle."
            ),
        )

    for key, (label, (lo, hi)) in _METRIC_BOUNDS.items():
        value = summary.get(key)
        if value is None:
            continue
        if not (lo <= value <= hi):
            return GateResult(
                hard_fail=True,
                low_confidence=False,
                reason=f"implausible_{label.replace(' ', '_')}",
                reason_metric=key,
                detected_stride_count=detected,
                usable_stride_count=usable,
                computed_cadence=cadence,
                user_message=(
                    f"The {label} we measured ({value}) isn't physiologically "
                    "plausible, which usually means the stride detector got "
                    "confused on this clip rather than a real reading. Try a "
                    "clearer side-on angle with your full body in frame."
                ),
            )

    low_confidence = usable < MIN_STRIDES_FOR_CONFIDENT
    return GateResult(
        hard_fail=False,
        low_confidence=low_confidence,
        reason=None,
        reason_metric=None,
        detected_stride_count=detected,
        usable_stride_count=usable,
        computed_cadence=cadence,
    )

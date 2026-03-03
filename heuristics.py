"""
Rule-based gait flags and recommendations. Uses fixed thresholds; in a web app
these could be user or cohort-specific. Accepts results dict (summary + strides),
returns list of flag dicts to be merged into results["flags"].
"""

# Overstriding: foot strike >10 cm ahead of hip COM (in image plane)
OVERSTRIDE_CM_THRESHOLD = 10

# Low cadence: below 170 steps per minute (evidence-based target for many runners)
CADENCE_MIN_SPM = 170

# Excessive vertical oscillation: >10 cm (wasted energy, often overstriding)
VERTICAL_OSC_MAX_CM = 10

# Insufficient knee flexion at foot strike: <15° (increases impact, injury risk)
KNEE_FLEXION_MIN_DEG = 15

# Excessive forward trunk lean: >15° (can cause lower back stress)
TRUNK_LEAN_MAX_DEG = 15


def evaluate_heuristics(results):
    """
    Generate flags and recommendations from summary and per-stride metrics.

    Args:
        results: Dict with "summary" and "strides" (from metrics.compute_metrics).

    Returns:
        List of dicts: {"metric", "value", "threshold", "recommendation"}.
    """
    flags = []
    summary = results.get("summary", {})
    strides = results.get("strides", [])

    _check_cadence(summary, strides, flags)
    _check_vertical_osc(summary, strides, flags)
    _check_knee_flexion(strides, flags)
    _check_overstriding(summary, strides, flags)
    _check_trunk_lean(summary, strides, flags)

    return flags


def _check_cadence(summary, strides, flags):
    avg = summary.get("cadence_avg")
    if avg is None:
        return
    if avg < CADENCE_MIN_SPM:
        flags.append({
            "metric": "cadence",
            "value": avg,
            "threshold": CADENCE_MIN_SPM,
            "recommendation": (
                f"Your cadence is low at {avg:.0f} spm. "
                "Try shortening your stride and increasing turnover."
            ),
        })


def _check_vertical_osc(summary, strides, flags):
    avg = summary.get("vertical_osc_avg_cm")
    if avg is None:
        return
    if avg > VERTICAL_OSC_MAX_CM:
        flags.append({
            "metric": "vertical_oscillation",
            "value": avg,
            "threshold": VERTICAL_OSC_MAX_CM,
            "recommendation": (
                f"Vertical oscillation is high at {avg:.1f} cm. "
                "Focus on a quick, compact stride and landing under your center of mass."
            ),
        })


def _check_knee_flexion(strides, flags):
    values = [s.get("knee_angle_strike_deg") for s in strides if s.get("knee_angle_strike_deg") is not None]
    if not values:
        return
    avg = sum(values) / len(values)
    if avg < KNEE_FLEXION_MIN_DEG:
        flags.append({
            "metric": "knee_flexion_at_strike",
            "value": round(avg, 1),
            "threshold": KNEE_FLEXION_MIN_DEG,
            "recommendation": (
                f"Knee flexion at foot strike is low ({avg:.1f}°). "
                "Aim for a slight bend at landing to absorb impact."
            ),
        })


def _check_overstriding(summary, strides, flags):
    values = [s.get("foot_strike_position_cm") for s in strides if s.get("foot_strike_position_cm") is not None]
    if not values:
        return
    avg = sum(values) / len(values)
    if avg > OVERSTRIDE_CM_THRESHOLD:
        flags.append({
            "metric": "overstriding",
            "value": round(avg, 2),
            "threshold": OVERSTRIDE_CM_THRESHOLD,
            "recommendation": (
                f"Foot strike is {avg:.1f} cm ahead of your hip (overstriding). "
                "Try landing with your foot under your center of mass and increasing cadence."
            ),
        })


def _check_trunk_lean(summary, strides, flags):
    values = [s.get("trunk_lean_deg") for s in strides if s.get("trunk_lean_deg") is not None]
    if not values:
        return
    avg = sum(values) / len(values)
    if avg > TRUNK_LEAN_MAX_DEG:
        flags.append({
            "metric": "trunk_lean",
            "value": round(avg, 1),
            "threshold": TRUNK_LEAN_MAX_DEG,
            "recommendation": (
                f"Forward trunk lean is {avg:.1f}°. "
                "A more upright posture can reduce lower back load."
            ),
        })

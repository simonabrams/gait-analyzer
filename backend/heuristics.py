"""
Rule-based gait flags and recommendations.
"""

OVERSTRIDE_CM_THRESHOLD = 10
CADENCE_MIN_SPM = 170
VERTICAL_OSC_MAX_CM = 10
KNEE_FLEXION_MIN_DEG = 15
TRUNK_LEAN_MAX_DEG = 15
CADENCE_CONFIDENCE_LOW_THRESHOLD = 0.5


def cadence_confidence(fps, ankle_visibility_scores, stride_count):
    """
    Return a 0–1 confidence score for the cadence measurement.

    Args:
        fps: Frames per second of the video.
        ankle_visibility_scores: Iterable of per-frame ankle landmark visibility
            values (0–1). May contain None entries which are ignored.
        stride_count: Number of detected strides.

    Returns:
        Float in [0, 1]. Values below CADENCE_CONFIDENCE_LOW_THRESHOLD indicate
        unreliable cadence estimates.
    """
    fps_score = min(fps / 60.0, 1.0) if fps and fps > 0 else 0.0
    vis_values = [v for v in ankle_visibility_scores if v is not None]
    vis_score = sum(vis_values) / len(vis_values) if vis_values else 0.0
    stride_score = min(stride_count / 5.0, 1.0) if stride_count else 0.0
    return round((fps_score + vis_score + stride_score) / 3.0, 3)


def evaluate_heuristics(results):
    flags = []
    summary = results.get("summary", {})
    strides = results.get("strides", [])

    _check_cadence(summary, strides, flags)
    _check_vertical_osc(summary, strides, flags)
    _check_knee_flexion(strides, flags)
    _check_overstriding(summary, strides, flags)
    _check_trunk_lean(summary, strides, flags)
    _check_cadence_confidence(summary, flags)

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


def _check_cadence_confidence(summary, flags):
    conf = summary.get("cadence_confidence")
    if conf is not None and conf < CADENCE_CONFIDENCE_LOW_THRESHOLD:
        flags.append({
            "metric": "cadence_confidence",
            "value": conf,
            "threshold": CADENCE_CONFIDENCE_LOW_THRESHOLD,
            "recommendation": (
                f"Cadence measurement confidence is low ({conf:.2f}). "
                "Results may be unreliable. Consider using a higher frame rate "
                "camera or ensuring ankles are clearly visible throughout the run."
            ),
        })

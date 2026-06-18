"""
Rule-based gait flags and recommendations.
"""

OVERSTRIDE_CM_SEVERE = 20
OVERSTRIDE_CM_THRESHOLD = 10
CADENCE_MIN_SPM = 170
CADENCE_SEVERE_SPM = 160
VERTICAL_OSC_MAX_CM = 10
VERTICAL_OSC_SEVERE_CM = 13
KNEE_FLEXION_MIN_DEG = 15
KNEE_FLEXION_SEVERE_DEG = 8
TRUNK_LEAN_MAX_DEG = 15
TRUNK_LEAN_SEVERE_DEG = 20
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

    # Collect raw flags before conflict resolution
    raw_flags = []
    _check_cadence(summary, strides, raw_flags)
    _check_vertical_osc(summary, strides, raw_flags)
    _check_knee_flexion(strides, raw_flags)
    _check_overstriding(summary, strides, raw_flags)
    _check_trunk_lean(summary, strides, raw_flags)
    _check_cadence_confidence(summary, flags)

    _resolve_flag_conflicts(raw_flags, flags)

    return flags


def _resolve_flag_conflicts(raw_flags, out):
    """
    Merge co-occurring flags that share a root cause into a single priority card.
    Currently: cadence + overstriding merge into one "shorten your stride" card.
    All other flags pass through unchanged.
    """
    metrics = {f["metric"]: f for f in raw_flags}

    cadence_flag = metrics.pop("cadence", None)
    overstride_flag = metrics.pop("overstriding", None)

    if cadence_flag and overstride_flag:
        avg_cadence = cadence_flag["value"]
        avg_overstride = overstride_flag["value"]
        target_spm = round(avg_cadence * 1.05)
        severity = "severe" if avg_cadence < CADENCE_SEVERE_SPM else "moderate"

        merged = {
            "metric": "stride_and_cadence",
            "value": avg_cadence,
            "threshold": CADENCE_MIN_SPM,
            "severity": severity,
            "recommendation": (
                f"Your cadence is low ({avg_cadence:.0f} spm) and your foot lands "
                f"{avg_overstride:.1f} cm ahead of your hips — these two issues share the "
                f"same fix. Increasing your step rate will automatically shorten your stride "
                f"and bring your foot landing under your centre of mass."
            ),
            "exercises": [
                {
                    "name": f"Metronome running at {target_spm} spm",
                    "description": (
                        f"Set a free metronome app to {target_spm} bpm (+5% from your current "
                        f"{avg_cadence:.0f} spm) and run in time with it for 3 × 3-minute "
                        f"intervals at easy pace. This is the single highest-ROI change you "
                        f"can make — faster turnover shortens the stride and eliminates the "
                        f"braking force of overstriding."
                    ),
                },
                {
                    "name": "Forward lean drill",
                    "description": (
                        "Stand tall, then lean your whole body forward from the ankles (not "
                        "the waist) until gravity pulls you into a step. That first foot "
                        "should land directly under your hip. Practice 8 × 10 m at easy pace "
                        "focusing solely on this lean — it naturally shortens your stride."
                    ),
                },
                {
                    "name": "High-knee skips",
                    "description": (
                        "3 × 20 m. Drive each knee up quickly and focus on a light, fast "
                        "ground contact. This reinforces quick turnover without the complexity "
                        "of full running speed."
                    ),
                },
            ],
        }
        out.append(merged)
    elif cadence_flag:
        out.append(cadence_flag)
    elif overstride_flag:
        out.append(overstride_flag)

    # All remaining flags pass through in original order
    for flag in raw_flags:
        if flag["metric"] in metrics:
            out.append(flag)


def _check_cadence(summary, strides, flags):
    avg = summary.get("cadence_avg")
    if avg is None:
        return
    if avg >= CADENCE_MIN_SPM:
        return

    target_spm = round(avg * 1.05)
    severity = "severe" if avg < CADENCE_SEVERE_SPM else "moderate"

    if severity == "severe":
        recommendation = (
            f"Your cadence is significantly low at {avg:.0f} spm (target: {CADENCE_MIN_SPM}+). "
            f"This is typically the biggest source of wasted energy and impact in recreational runners. "
            f"Start by targeting {target_spm} spm — a 5% increase — before pushing higher."
        )
    else:
        recommendation = (
            f"Your cadence is slightly low at {avg:.0f} spm. "
            f"Try increasing turnover to {target_spm} spm (+5%) — "
            f"a small step-rate boost reduces braking force and knee load."
        )

    flags.append({
        "metric": "cadence",
        "value": avg,
        "threshold": CADENCE_MIN_SPM,
        "severity": severity,
        "recommendation": recommendation,
        "exercises": [
            {
                "name": f"Metronome running at {target_spm} spm",
                "description": (
                    f"Set a free metronome app to {target_spm} bpm and run in time with the beat "
                    f"for 2–3 min intervals. Your current pace of {avg:.0f} spm means each step "
                    f"is slightly too long — the metronome retrains the rhythm quickly."
                ),
            },
            {
                "name": "High-knee skips",
                "description": (
                    "3 × 20 m. Drive each knee up quickly and focus on a light, fast "
                    "ground contact — this reinforces the quick-turnover habit without "
                    "the complexity of full running."
                ),
            },
            {
                "name": "Fast feet drill",
                "description": (
                    "On the spot or over a short 10 m strip, take tiny rapid steps as "
                    "fast as possible for 10 s. Rest 20 s. Repeat 4–6 times to train "
                    "neuromuscular speed."
                ),
            },
        ],
    })


def _check_vertical_osc(summary, strides, flags):
    avg = summary.get("vertical_osc_avg_cm")
    if avg is None:
        return
    if avg <= VERTICAL_OSC_MAX_CM:
        return

    severity = "severe" if avg > VERTICAL_OSC_SEVERE_CM else "moderate"
    excess = avg - VERTICAL_OSC_MAX_CM

    if severity == "severe":
        recommendation = (
            f"Vertical oscillation is high at {avg:.1f} cm — {excess:.1f} cm above the "
            f"{VERTICAL_OSC_MAX_CM} cm target. This much up-and-down bounce is a significant "
            f"energy leak. Focus on driving forward, not upward."
        )
    else:
        recommendation = (
            f"Vertical oscillation is slightly elevated at {avg:.1f} cm "
            f"(target: ≤{VERTICAL_OSC_MAX_CM} cm). "
            f"A more compact stride and quicker cadence will reduce wasted bounce."
        )

    flags.append({
        "metric": "vertical_oscillation",
        "value": avg,
        "threshold": VERTICAL_OSC_MAX_CM,
        "severity": severity,
        "recommendation": recommendation,
        "exercises": [
            {
                "name": "Banded hip marches",
                "description": (
                    "Place a light resistance band just above your knees and march "
                    "on the spot, focusing on driving hips forward rather than upward. "
                    "3 × 30 reps builds the hip-drive pattern that keeps you low."
                ),
            },
            {
                "name": "Wall-lean running drill",
                "description": (
                    "Lean against a wall at 45° and drive alternating knees up "
                    "with a quick, flat foot contact. Emphasise forward momentum, "
                    "not bounce. 3 × 20 reps each side."
                ),
            },
            {
                "name": "Cadence focus intervals",
                "description": (
                    f"Run 4 × 1 min at your target pace with a conscious focus on "
                    f"shortening stride and increasing turnover. Higher cadence naturally "
                    f"reduces bounce — aim to bring oscillation below {VERTICAL_OSC_MAX_CM} cm."
                ),
            },
        ],
    })


def _check_knee_flexion(strides, flags):
    values = [s.get("knee_angle_strike_deg") for s in strides if s.get("knee_angle_strike_deg") is not None]
    if not values:
        return
    avg = sum(values) / len(values)
    if avg >= KNEE_FLEXION_MIN_DEG:
        return

    severity = "severe" if avg < KNEE_FLEXION_SEVERE_DEG else "moderate"
    deficit = KNEE_FLEXION_MIN_DEG - avg

    if severity == "severe":
        recommendation = (
            f"Knee flexion at foot strike is very low ({avg:.1f}°) — you're landing with "
            f"nearly a straight leg, {deficit:.0f}° short of the {KNEE_FLEXION_MIN_DEG}° target. "
            f"This transmits impact directly through the knee and hip with little absorption."
        )
    else:
        recommendation = (
            f"Knee flexion at foot strike is low ({avg:.1f}°). "
            f"Aim for a slight bend of at least {KNEE_FLEXION_MIN_DEG}° at landing "
            f"to absorb impact and protect the knee."
        )

    flags.append({
        "metric": "knee_flexion_at_strike",
        "value": round(avg, 1),
        "threshold": KNEE_FLEXION_MIN_DEG,
        "severity": severity,
        "recommendation": recommendation,
        "exercises": [
            {
                "name": "Hamstring curls",
                "description": (
                    f"3 × 12 reps with a resistance band or machine. Your strike angle of "
                    f"{avg:.0f}° suggests the hamstrings aren't firing early enough at contact — "
                    f"targeted strengthening here helps you maintain the knee bend needed."
                ),
            },
            {
                "name": "Butt kicks",
                "description": (
                    "Jog slowly and flick your heels up toward your glutes with each "
                    "step. 3 × 20 m. This cues the knee-bend pattern your body needs "
                    "to replicate at full running speed."
                ),
            },
            {
                "name": "Single-leg Romanian deadlift",
                "description": (
                    "3 × 8 each side with a light dumbbell. Builds posterior-chain "
                    "strength and balance so you can land softly with a bent knee "
                    "rather than bracing into a locked leg."
                ),
            },
        ],
    })


def _check_overstriding(summary, strides, flags):
    values = [s.get("foot_strike_position_cm") for s in strides if s.get("foot_strike_position_cm") is not None]
    if not values:
        return
    avg = sum(values) / len(values)
    if avg <= OVERSTRIDE_CM_THRESHOLD:
        return

    severity = "severe" if avg > OVERSTRIDE_CM_SEVERE else "moderate"

    if severity == "severe":
        recommendation = (
            f"Foot strike is {avg:.1f} cm ahead of your hip — significantly overstriding. "
            f"Every step creates a large braking force that wastes energy and loads the knee. "
            f"The fastest fix is increasing your cadence, which automatically shortens your stride."
        )
    else:
        recommendation = (
            f"Foot strike is {avg:.1f} cm ahead of your hip (target: ≤{OVERSTRIDE_CM_THRESHOLD} cm). "
            f"Try landing with your foot under your centre of mass and increasing cadence."
        )

    flags.append({
        "metric": "overstriding",
        "value": round(avg, 2),
        "threshold": OVERSTRIDE_CM_THRESHOLD,
        "severity": severity,
        "recommendation": recommendation,
        "exercises": [
            {
                "name": "Forward lean drill",
                "description": (
                    "Stand tall, then lean your whole body forward from the ankles "
                    "(not the waist) until gravity pulls you into a step. That first "
                    "foot should land under your hip — not out in front. "
                    "Practice 10 × 10 m at easy pace focusing on this lean."
                ),
            },
            {
                "name": "Barefoot strides",
                "description": (
                    f"On soft grass, do 6 × 60 m strides in bare feet or minimal shoes. "
                    f"The ground feedback naturally discourages the heel-first landing that "
                    f"accompanies your {avg:.1f} cm overstride."
                ),
            },
            {
                "name": "Short-stride cadence intervals",
                "description": (
                    f"Run 5 × 2 min consciously shortening each stride while keeping pace. "
                    f"A shorter stride means your foot lands closer to your centre of mass — "
                    f"the most direct fix for {avg:.1f} cm of overstriding."
                ),
            },
        ],
    })


def _check_trunk_lean(summary, strides, flags):
    values = [s.get("trunk_lean_deg") for s in strides if s.get("trunk_lean_deg") is not None]
    if not values:
        return
    avg = sum(values) / len(values)
    if avg <= TRUNK_LEAN_MAX_DEG:
        return

    severity = "severe" if avg > TRUNK_LEAN_SEVERE_DEG else "moderate"
    excess = avg - TRUNK_LEAN_MAX_DEG

    if severity == "severe":
        recommendation = (
            f"Forward trunk lean is {avg:.1f}° — {excess:.0f}° beyond the {TRUNK_LEAN_MAX_DEG}° target. "
            f"This degree of forward collapse puts significant load on the lower back and "
            f"reduces your ability to drive the hips through properly."
        )
    else:
        recommendation = (
            f"Forward trunk lean is {avg:.1f}° (target: ≤{TRUNK_LEAN_MAX_DEG}°). "
            f"A more upright posture reduces lower back load and improves hip drive."
        )

    flags.append({
        "metric": "trunk_lean",
        "value": round(avg, 1),
        "threshold": TRUNK_LEAN_MAX_DEG,
        "severity": severity,
        "recommendation": recommendation,
        "exercises": [
            {
                "name": "Dead bug",
                "description": (
                    "Lie on your back, arms pointing to the ceiling, knees at 90°. "
                    "Slowly lower opposite arm and leg toward the floor while keeping "
                    "your lower back pressed down. 3 × 8 each side. Builds the deep "
                    "core stability that holds your trunk upright at pace."
                ),
            },
            {
                "name": "Plank progressions",
                "description": (
                    "Build from a standard forearm plank (3 × 30 s) to a plank with "
                    "alternating shoulder taps (3 × 10 each side). Strong anterior "
                    "core muscles resist forward collapse when you're tired."
                ),
            },
            {
                "name": "Wall-posture running cue",
                "description": (
                    f"Stand against a wall — head, shoulders and glutes touching. "
                    f"Memorise that upright feeling, then replicate it as you run. "
                    f"Your lean of {avg:.0f}° will reduce naturally as core endurance builds. "
                    f"Do 4 × 1 min easy runs with this cue before building back to full effort."
                ),
            },
        ],
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

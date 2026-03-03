"""
Generate a plain-text summary report from the results dict. Returns a string;
caller prints or saves to .txt. In a web app, could render this or use the
same structure for HTML.
"""


def generate_report(results):
    """
    Build a text report from results (summary, flags, recommendations).

    Args:
        results: Full results dict (e.g. loaded from results.json).

    Returns:
        String suitable for console or .txt file.
    """
    summary = results.get("summary", {})
    flags = results.get("flags", [])
    meta = results.get("meta", {})

    lines = [
        "Gait Analysis Report",
        "=" * 50,
        "",
        f"Video: {meta.get('video_file', 'N/A')}",
        f"Height: {meta.get('height_cm', 'N/A')} cm",
        f"Analyzed: {meta.get('analyzed_at', 'N/A')}",
        f"Strides analyzed: {summary.get('num_strides', 0)}",
        "",
    ]

    lines.append("Summary (averages)")
    lines.append("-" * 40)
    lines.append(f"  Cadence:           {summary.get('cadence_avg', '—')} spm  (target ≥170)")
    lines.append(f"  Vertical osc:      {summary.get('vertical_osc_avg_cm', '—')} cm   (target ≤10)")
    lines.append(f"  Knee @ strike:     {summary.get('knee_angle_strike_avg_deg', '—')}°   (target ≥15°)")
    lines.append(f"  Foot strike pos:   {summary.get('foot_strike_position_avg_cm', '—')} cm   (target ≤10)")
    lines.append(f"  Trunk lean:        {summary.get('trunk_lean_avg_deg', '—')}°   (target ≤15°)")
    lines.append("")

    total_metrics = 5
    passed = total_metrics - len(flags)
    lines.append(f"Overall score: {passed}/{total_metrics} metrics within target")
    lines.append("")

    if flags:
        lines.append("Flagged issues and recommendations")
        lines.append("-" * 40)
        for f in flags:
            lines.append(f"  • {f.get('metric', '')}: value {f.get('value')} (threshold: {f.get('threshold')})")
            lines.append(f"    {f.get('recommendation', '')}")
            lines.append("")
    else:
        lines.append("No issues flagged. Metrics within target ranges.")
        lines.append("")

    lines.append("=" * 50)
    return "\n".join(lines)

"""
Generate a matplotlib multi-panel dashboard from the results dict.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def create_dashboard(results):
    fig = plt.figure(figsize=(14, 10))
    strides = results.get("strides", [])
    summary = results.get("summary", {})
    results.get("flags", [])

    ax1 = fig.add_subplot(2, 2, 1)
    if strides:
        cadences = [s["cadence"] for s in strides]
        ax1.plot(range(1, len(cadences) + 1), cadences, "b-o", markersize=4)
        ax1.axhline(y=170, color="gray", linestyle="--", label="Target 170 spm")
    ax1.set_xlabel("Stride number")
    ax1.set_ylabel("Cadence (spm)")
    ax1.set_title("Cadence over time")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(2, 2, 2)
    if strides:
        oscs = [s["vertical_osc_cm"] for s in strides]
        ax2.plot(range(1, len(oscs) + 1), oscs, "g-o", markersize=4)
        ax2.axhline(y=10, color="gray", linestyle="--", label="Max 10 cm")
    ax2.set_xlabel("Stride number")
    ax2.set_ylabel("Vertical oscillation (cm)")
    ax2.set_title("Vertical oscillation over time")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ax3 = fig.add_subplot(2, 2, 3)
    if strides:
        knees = [s.get("knee_angle_strike_deg") or 0 for s in strides]
        x = range(1, len(knees) + 1)
        colors = ["red" if (k and k < 15) else "steelblue" for k in knees]
        ax3.bar(x, knees, color=colors)
        ax3.axhline(y=15, color="gray", linestyle="--", label="Min 15°")
    ax3.set_xlabel("Stride number")
    ax3.set_ylabel("Knee angle at strike (°)")
    ax3.set_title("Knee flexion at foot strike")
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis="y")

    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis("off")
    lines = ["Summary", "—" * 20]
    metrics_config = [
        ("Cadence (spm)", "cadence_avg", 170, "≥170", "spm"),
        ("Vertical osc (cm)", "vertical_osc_avg_cm", 10, "≤10", "cm"),
        ("Knee @ strike (°)", "knee_angle_strike_avg_deg", 15, "≥15", "°"),
        ("Foot strike (cm)", "foot_strike_position_avg_cm", 10, "≤10", "cm"),
        ("Trunk lean (°)", "trunk_lean_avg_deg", 15, "≤15", "°"),
    ]
    passed = 0
    for label, key, threshold, target_str, unit in metrics_config:
        val = summary.get(key)
        if val is None:
            lines.append(f"{label}: —")
            continue
        if key == "cadence_avg":
            ok = val >= threshold
        elif key == "knee_angle_strike_avg_deg":
            ok = val >= threshold
        else:
            ok = val <= threshold
        if ok:
            passed += 1
        status = "✓" if ok else "✗"
        lines.append(f"{label}: {val} {unit} (target {target_str}) {status}")
    total = len([m for m in metrics_config if summary.get(m[1]) is not None])
    lines.append("")
    lines.append(f"Score: {passed}/{total} metrics passed")
    ax4.text(0.1, 0.95, "\n".join(lines), transform=ax4.transAxes,
             fontsize=10, verticalalignment="top", fontfamily="monospace")

    plt.tight_layout()
    return fig

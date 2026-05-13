"""
Generate a matplotlib multi-panel dashboard from the results dict.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Site design tokens
BG_DARK = "#0F0F0F"
BG_PANEL = "#1A1A1A"
COLOR_PRIMARY = "#00C896"
COLOR_WARN = "#FF6B6B"
COLOR_GRID = "#2A2A2A"
COLOR_AXIS = "#555555"
COLOR_TEXT = "#E0E0E0"
COLOR_TEXT_DIM = "#888888"
COLOR_TARGET = "#555555"


def _style_ax(ax, title, xlabel, ylabel):
    ax.set_facecolor(BG_PANEL)
    ax.set_title(title, color=COLOR_TEXT, fontsize=11, fontweight="semibold", pad=10)
    ax.set_xlabel(xlabel, color=COLOR_TEXT_DIM, fontsize=9, labelpad=6)
    ax.set_ylabel(ylabel, color=COLOR_TEXT_DIM, fontsize=9, labelpad=6)
    ax.tick_params(colors=COLOR_TEXT_DIM, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(COLOR_GRID)
    ax.grid(True, color=COLOR_GRID, linewidth=0.7, linestyle="-", alpha=1)
    ax.set_axisbelow(True)


def create_dashboard(results):
    strides = results.get("strides", [])
    summary = results.get("summary", {})

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.patch.set_facecolor(BG_DARK)
    fig.subplots_adjust(hspace=0.42, wspace=0.28, left=0.07, right=0.97, top=0.93, bottom=0.08)

    xs = list(range(1, len(strides) + 1))

    # ── Cadence ──────────────────────────────────────────────────────────────
    ax1 = axes[0, 0]
    _style_ax(ax1, "Cadence", "Stride", "spm")
    if strides:
        cadences = [s["cadence"] for s in strides]
        ax1.plot(xs, cadences, color=COLOR_PRIMARY, linewidth=1.8, marker="o",
                 markersize=3.5, markerfacecolor=COLOR_PRIMARY, zorder=3)
        ax1.axhline(y=170, color=COLOR_TARGET, linewidth=1.2, linestyle="--",
                    label="Target ≥170 spm", zorder=2)
        ax1.legend(fontsize=8, facecolor=BG_PANEL, edgecolor=COLOR_GRID,
                   labelcolor=COLOR_TEXT_DIM, framealpha=1)
        ax1.set_xlim(0.5, len(xs) + 0.5)

    # ── Vertical oscillation ─────────────────────────────────────────────────
    ax2 = axes[0, 1]
    _style_ax(ax2, "Vertical Oscillation", "Stride", "cm")
    if strides:
        oscs = [s["vertical_osc_cm"] for s in strides]
        ax2.plot(xs, oscs, color=COLOR_PRIMARY, linewidth=1.8, marker="o",
                 markersize=3.5, markerfacecolor=COLOR_PRIMARY, zorder=3)
        ax2.axhline(y=10, color=COLOR_TARGET, linewidth=1.2, linestyle="--",
                    label="Max 10 cm", zorder=2)
        ax2.legend(fontsize=8, facecolor=BG_PANEL, edgecolor=COLOR_GRID,
                   labelcolor=COLOR_TEXT_DIM, framealpha=1)
        ax2.set_xlim(0.5, len(xs) + 0.5)

    # ── Knee flexion ─────────────────────────────────────────────────────────
    ax3 = axes[1, 0]
    _style_ax(ax3, "Knee Flexion at Foot Strike", "Stride", "degrees")
    if strides:
        knees = [s.get("knee_angle_strike_deg") or 0 for s in strides]
        bar_colors = [COLOR_WARN if (k and k < 15) else COLOR_PRIMARY for k in knees]
        ax3.bar(xs, knees, color=bar_colors, width=0.7, zorder=3)
        ax3.axhline(y=15, color=COLOR_TARGET, linewidth=1.2, linestyle="--",
                    label="Min 15°", zorder=4)
        ax3.legend(fontsize=8, facecolor=BG_PANEL, edgecolor=COLOR_GRID,
                   labelcolor=COLOR_TEXT_DIM, framealpha=1)
        ax3.set_xlim(0.5, len(xs) + 0.5)

    # ── Foot strike position ─────────────────────────────────────────────────
    ax4 = axes[1, 1]
    _style_ax(ax4, "Foot Strike Position", "Stride", "cm ahead of hip")
    foot_vals = [s.get("foot_strike_position_cm") for s in strides if s.get("foot_strike_position_cm") is not None]
    if foot_vals:
        xs4 = [i + 1 for i, s in enumerate(strides) if s.get("foot_strike_position_cm") is not None]
        bar_colors4 = [COLOR_WARN if v > 10 else COLOR_PRIMARY for v in foot_vals]
        ax4.bar(xs4, foot_vals, color=bar_colors4, width=0.7, zorder=3)
        ax4.axhline(y=10, color=COLOR_TARGET, linewidth=1.2, linestyle="--",
                    label="Target ≤10 cm", zorder=4)
        ax4.legend(fontsize=8, facecolor=BG_PANEL, edgecolor=COLOR_GRID,
                   labelcolor=COLOR_TEXT_DIM, framealpha=1)
        ax4.set_xlim(0.5, max(xs4) + 0.5)
    else:
        ax4.set_facecolor(BG_PANEL)
        ax4.text(0.5, 0.5, "No foot strike data", transform=ax4.transAxes,
                 ha="center", va="center", color=COLOR_TEXT_DIM, fontsize=10)
        for spine in ax4.spines.values():
            spine.set_edgecolor(COLOR_GRID)

    return fig

import type { Flag } from "@/lib/api";
import { METRIC_TARGETS } from "@/lib/metricTargets";
import { STATUS_BADGE_CLASSES, STATUS_LABEL, statusForMetric } from "@/lib/gaitStatus";
import MetricTooltip from "@/components/MetricTooltip";

interface MetricCardsProps {
  summary: Record<string, unknown> | undefined;
  flags: Flag[] | undefined;
}

// Which flag(s) a tile's status comes from — includes the merged-flag name
// (see gaitStatus.ts) for metrics that can fold together in heuristics.py.
const TILE_CONFIG = [
  {
    ...METRIC_TARGETS.cadence,
    label: "CADENCE", // overrides METRIC_TARGETS' own title-case label — must come AFTER the spread
    flagMetrics: ["cadence", "stride_and_cadence"],
    tooltip: "Measured by detecting stride cycles in your video. Accurate to ±2–3% under good filming conditions.",
    format: (v: number) => String(Math.round(v)),
  },
  {
    ...METRIC_TARGETS.bounce,
    label: "BOUNCE",
    flagMetrics: ["vertical_oscillation"],
    tooltip: "Estimated from vertical movement of torso landmarks. Best compared session-to-session, not against wearables.",
    format: (v: number) => String(Math.round(v)),
  },
  {
    ...METRIC_TARGETS.kneeDrive,
    label: "KNEE DRIVE",
    flagMetrics: ["knee_flexion_at_strike"],
    tooltip: "Joint angles from a single camera view are reliable within ~10% vs. lab-grade motion capture under optimal conditions.",
    format: (v: number) => String(Math.round(v)),
  },
  {
    ...METRIC_TARGETS.footStrike,
    label: "FOOT STRIKE",
    flagMetrics: ["overstriding", "stride_and_cadence"],
    tooltip: "How far ahead of your hip your foot lands at contact — landing closer to under your hip reduces braking force.",
    format: (v: number) => v.toFixed(1),
  },
] as const;

export default function MetricCards({ summary, flags }: MetricCardsProps) {
  if (!summary) return null;
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4">
      {TILE_CONFIG.map(({ label, key, unit, target, tooltip, flagMetrics, format }) => {
        const raw = summary[key];
        const numVal = raw != null ? Number(raw) : null;
        const status = numVal != null ? statusForMetric(flags, [...flagMetrics]) : "good";
        const display = numVal != null ? format(numVal) : "—";

        return (
          <div
            key={key}
            className={`bg-secondary border rounded-xl p-4 ${
              status === "focus" ? "border-red-400/40 ring-1 ring-inset ring-red-400/20" : "border-white/10"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center">
                <span className="font-mono text-[11px] tracking-[0.12em] text-gray-400 uppercase">
                  {label}
                </span>
                <MetricTooltip content={tooltip} />
              </div>
              {numVal != null && (
                <span className={`text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${STATUS_BADGE_CLASSES[status]}`}>
                  {STATUS_LABEL[status]}
                </span>
              )}
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-[28px] font-semibold text-white leading-none">{display}</span>
              <span className="text-sm text-gray-400">{unit}</span>
            </div>
            <p className="text-xs text-gray-500 mt-1.5">Target {targetLabel(key, target, unit)}</p>
          </div>
        );
      })}
    </div>
  );
}

/** "≥170 SPM" / "≤10 cm" — direction inferred from which comparison the
 * metric's own `good()` predicate uses, so the label can't drift out of
 * sync with the actual rule. */
function targetLabel(key: string, target: number, unit: string): string {
  const cfg = Object.values(METRIC_TARGETS).find((t) => t.key === key);
  if (!cfg) return `${target} ${unit}`;
  const isMin = cfg.good(target + 1) && !cfg.good(target - 1);
  return `${isMin ? "≥" : "≤"}${target} ${unit}`;
}

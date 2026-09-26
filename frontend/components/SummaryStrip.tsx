import type { Flag, RearView } from "@/lib/api";
import { displayedBalance } from "@/lib/rearBalance";
import { findingFlags, formatFlagValue, humanFlagLabel, humanFlagTitle, sortBySeverity, statusForMetric } from "@/lib/gaitStatus";

const TILE_METRICS = [
  { key: "cadence_avg", flagMetrics: ["cadence", "stride_and_cadence"], label: "cadence" },
  { key: "vertical_osc_avg_cm", flagMetrics: ["vertical_oscillation"], label: "bounce" },
  { key: "knee_angle_strike_avg_deg", flagMetrics: ["knee_flexion_at_strike"], label: "knee drive" },
  { key: "foot_strike_position_avg_cm", flagMetrics: ["overstriding", "stride_and_cadence"], label: "foot strike" },
] as const;

function joinList(items: string[]): string {
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

interface SummaryStripProps {
  summary: Record<string, unknown> | undefined;
  flags: Flag[] | undefined;
  /** Only used to optionally mention a real rear finding in the verdict
   * prose (via rear's own backend-computed symmetry band) — never to
   * generate a "FIX FIRST" chip, since rear has no card in "What to work
   * on" to link to (see lib/gaitStatus.ts's header comment). */
  rearView?: RearView | null;
}

/** One generated verdict sentence + up to 2 "FIX FIRST" chips. Every word is
 * derived from real flags/status (never hardcoded), so it can't contradict
 * the tiles or cards it summarizes — the exact failure mode the design
 * review's own mockup flagged as a "known contradiction" to avoid. */
export default function SummaryStrip({ summary, flags, rearView }: SummaryStripProps) {
  if (!summary) return null;

  const strengths = TILE_METRICS.filter(
    (t) => summary[t.key] != null && statusForMetric(flags, [...t.flagMetrics]) === "good",
  ).map((t) => t.label);

  const findings = sortBySeverity(findingFlags(flags)).filter((f) => f.metric !== "cadence_confidence");
  const seen = new Set<string>();
  const focusAreas: string[] = [];
  for (const f of findings) {
    if (seen.has(f.metric)) continue;
    seen.add(f.metric);
    focusAreas.push(humanFlagLabel(f.metric));
  }
  const balance = displayedBalance(rearView?.symmetry);
  if (balance && balance.band !== "symmetric") {
    focusAreas.push("left/right balance (rear view)");
  }

  // Side-only, worst-first, capped at 2 — matches what "What to work on"
  // actually has cards for (rear findings have no card to jump to here).
  const fixFirst = findings.slice(0, 2);

  return (
    <div className="bg-secondary border border-white/10 rounded-xl px-5 py-4 flex flex-wrap items-start justify-between gap-4">
      <p className="text-sm leading-relaxed max-w-2xl text-gray-300">
        {strengths.length > 0 && (
          <span className="text-primary font-medium">Solid {joinList(strengths)}. </span>
        )}
        {focusAreas.length > 0 ? (
          <>
            Main focus: <span className="text-red-400 font-medium">{joinList(focusAreas)}</span>.
          </>
        ) : strengths.length > 0 ? (
          "Nothing else flagged — keep it up."
        ) : (
          "Not enough data to generate a summary yet."
        )}
      </p>
      {fixFirst.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <span className="font-mono text-[11px] tracking-[0.12em] text-gray-500 uppercase">
            Fix First
          </span>
          {fixFirst.map((f) => (
            <a
              key={f.metric}
              href={`#finding-${f.metric}`}
              className="text-xs font-medium bg-red-400/10 text-red-300 border border-red-400/30 rounded-full px-3 py-1 hover:bg-red-400/20 transition-colors whitespace-nowrap"
            >
              {humanFlagTitle(f.metric)} · {formatFlagValue(f.value, f.metric)} →
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

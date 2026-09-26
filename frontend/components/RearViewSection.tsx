import type { RearLeg, RearMetric, RearMetricTier, RearSymmetry, RearView } from "@/lib/api";
import MetricTooltip from "@/components/MetricTooltip";
import { displayedBalance } from "@/lib/rearBalance";

/** Renders results.rear_view — knee alignment / step width and left/right
 * balance from an optional rear-view video (see backend/rear_metrics.py,
 * backend/rear_confidence.py). A separate component from MetricCards rather
 * than an extension of it: MetricCards is hardcoded to exactly 3 flat
 * side-view metrics, not shaped for per-leg/tiered data.
 *
 * Hip drop and pronation are never shown, for any run, even ones analysed
 * before they moved to `experimental` (see lib/rearBalance.ts for why), and
 * the balance score is rebuilt without them. Step width only appears when
 * present (metrics_version 2+). */
export default function RearViewSection({ rearView }: { rearView: RearView }) {
  if (rearView.status === "insufficient_data") {
    return (
      <div className="bg-secondary border border-white/10 rounded-xl p-5">
        <p className="text-sm text-gray-400">
          {rearView.confidence_gate?.user_message ??
            "We couldn't get a reliable read from the rear-view video."}
        </p>
      </div>
    );
  }

  // Defensive only — status "ok"/"low_confidence" always carries legs per the
  // backend schema; nothing to render without them.
  if (!rearView.legs) return null;

  return (
    <div className="space-y-4">
      {rearView.status === "low_confidence" && (
        <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-5 py-3 text-sm text-amber-300">
          Lower confidence than usual for the rear-view read — fewer usable strides detected
          than ideal.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <LegCard title="Left Leg" leg={rearView.legs.left} />
        <LegCard title="Right Leg" leg={rearView.legs.right} />
      </div>
      {rearView.symmetry && <SymmetryCard symmetry={rearView.symmetry} />}
      <p className="text-xs text-gray-500 text-center">
        Rear-view patterns are rougher than the side-view numbers above. Use them to spot
        left/right differences and changes between sessions.
      </p>
    </div>
  );
}

const TIER_STYLES: Record<RearMetricTier, string> = {
  low: "bg-white/10 text-gray-400",
  moderate: "bg-amber-400/15 text-amber-300",
  high: "bg-primary/15 text-primary",
};

/** How sure we are of the reading — a different axis from whether the
 * reading itself is good, so it says "reliability" rather than a bare tier. */
function ReliabilityBadge({ tier }: { tier: RearMetricTier }) {
  return (
    <span
      className={`text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded whitespace-nowrap ${TIER_STYLES[tier]}`}
      title="How consistent and trackable this reading was — not whether the result is good or bad."
    >
      {tier} reliability
    </span>
  );
}

const PATTERN_LABELS: Record<string, string> = {
  // hip drop
  typical: "Typical",
  elevated: "Elevated",
  pronounced: "Pronounced",
  // knee alignment (backend key: knee_valgus)
  neutral: "Tracks straight",
  valgus_pattern: "Knee tracks inward",
  varus_pattern: "Knee tracks outward",
  // step width
  narrow: "Narrow",
  crossover: "Crosses midline",
  // left/right balance bands
  symmetric: "Balanced",
  mild_asymmetry: "Slight difference",
  notable_asymmetry: "Noticeable difference",
};

function patternLabel(pattern: string): string {
  if (PATTERN_LABELS[pattern]) return PATTERN_LABELS[pattern];
  const spaced = pattern.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** Explicit +/- on every angle (not just an implied minus) — direction is
 * real, meaningful data here (inward vs. outward knee, drop vs. hike — see
 * backend/rear_confidence.py's pattern_for()), never collapsed to an
 * unsigned magnitude. Step width is a distance: % of hip width. */
function formatValue(metric: Extract<RearMetric, { available: true }>): string {
  if (metric.value_pct != null) return `${metric.value_pct}%`;
  const v = metric.value_deg ?? 0;
  return `${v > 0 ? "+" : ""}${v}°`;
}

function MetricRow({ label, metric }: { label: string; metric: RearMetric }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2.5 border-b border-white/5 last:border-b-0">
      <div className="flex items-center pt-0.5">
        <span className="text-sm text-gray-300">{label}</span>
        {metric.available && <MetricTooltip content={metric.disclaimer} />}
      </div>
      {metric.available ? (
        <div className="text-right">
          <div className="flex items-center gap-2 justify-end">
            <span className="text-white font-mono font-semibold text-sm">{formatValue(metric)}</span>
            <ReliabilityBadge tier={metric.confidence.tier} />
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            {patternLabel(metric.pattern)}
            {metric.value_pct != null && <span className="text-gray-500"> · of hip width</span>}
          </p>
        </div>
      ) : (
        <span className="text-xs text-gray-500 pt-0.5">Not enough data</span>
      )}
    </div>
  );
}

function LegCard({ title, leg }: { title: string; leg: RearLeg }) {
  return (
    <div className="bg-secondary border border-white/10 rounded-xl p-5">
      <p className="font-mono text-[11px] tracking-[0.12em] text-primary uppercase mb-1">{title}</p>
      <MetricRow label="Knee alignment" metric={leg.knee_valgus} />
      {leg.step_width && <MetricRow label="Step width" metric={leg.step_width} />}
    </div>
  );
}

function SymmetryCard({ symmetry }: { symmetry: RearSymmetry }) {
  const balance = displayedBalance(symmetry);
  if (!symmetry.available || !balance) {
    return (
      <div className="bg-secondary border border-white/10 rounded-xl p-5">
        <p className="text-sm text-gray-400">
          Not enough matching data on both legs to compare left and right.
        </p>
      </div>
    );
  }
  return (
    <div className="bg-secondary border border-white/10 rounded-xl p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <p className="font-mono text-[11px] tracking-[0.12em] text-primary uppercase">
            Left/right balance
          </p>
          <MetricTooltip content={symmetry.disclaimer} />
        </div>
        <ReliabilityBadge tier={symmetry.confidence.tier} />
      </div>
      <div className="flex items-baseline gap-2 mt-2">
        <span className="text-[28px] font-mono font-semibold text-white leading-none">{balance.score}</span>
        <span className="text-gray-400 text-sm">/ 100</span>
      </div>
      <p className="text-sm text-gray-300 mt-0.5">{patternLabel(balance.band)}</p>
    </div>
  );
}

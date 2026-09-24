import type { RearLeg, RearMetric, RearMetricTier, RearSymmetry, RearView } from "@/lib/api";
import MetricTooltip from "@/components/MetricTooltip";

/** Renders results.rear_view — the frontal-plane hip drop / pronation /
 * knee valgus / symmetry patterns from an optional rear-view video (see
 * backend/rear_metrics.py, backend/rear_confidence.py). A separate component
 * from MetricCards rather than an extension of it: MetricCards is hardcoded
 * to exactly 3 flat side-view metrics, not shaped for per-leg/tiered data. */
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
    </div>
  );
}

const TIER_STYLES: Record<RearMetricTier, string> = {
  low: "bg-white/10 text-gray-400",
  moderate: "bg-amber-400/15 text-amber-300",
  high: "bg-primary/15 text-primary",
};

function TierBadge({ tier }: { tier: RearMetricTier }) {
  return (
    <span
      className={`text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded whitespace-nowrap ${TIER_STYLES[tier]}`}
    >
      {tier}
    </span>
  );
}

/** "pronation_pattern" -> "Pronation pattern", "typical" -> "Typical". */
function formatPattern(pattern: string): string {
  const spaced = pattern.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
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
            <span className="text-white font-semibold text-sm">{metric.value_deg}°</span>
            <TierBadge tier={metric.confidence.tier} />
          </div>
          <p className="text-xs text-gray-400 mt-0.5">{formatPattern(metric.pattern)}</p>
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
      <p className="text-xs font-semibold tracking-widest text-primary uppercase mb-1">{title}</p>
      <MetricRow label="Hip Drop" metric={leg.hip_drop} />
      <MetricRow label="Pronation" metric={leg.pronation} />
      <MetricRow label="Knee Valgus" metric={leg.knee_valgus} />
    </div>
  );
}

function SymmetryCard({ symmetry }: { symmetry: RearSymmetry }) {
  if (!symmetry.available) {
    return (
      <div className="bg-secondary border border-white/10 rounded-xl p-5">
        <p className="text-sm text-gray-400">
          Not enough matching data on both legs to compute a symmetry score.
        </p>
      </div>
    );
  }
  return (
    <div className="bg-secondary border border-white/10 rounded-xl p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <p className="text-xs font-semibold tracking-widest text-primary uppercase">
            Left/Right Symmetry
          </p>
          <MetricTooltip content={symmetry.disclaimer} />
        </div>
        <TierBadge tier={symmetry.confidence.tier} />
      </div>
      <div className="flex items-baseline gap-2 mt-2">
        <span className="text-2xl font-bold text-white">{symmetry.score}</span>
        <span className="text-gray-400 text-sm">/ 100</span>
      </div>
      <p className="text-sm text-gray-300 mt-0.5">{formatPattern(symmetry.band)}</p>
    </div>
  );
}

interface Exercise {
  name: string;
  description: string;
}

interface Flag {
  metric: string;
  value?: unknown;
  threshold?: unknown;
  recommendation: string;
  exercises?: Exercise[];
}

interface FeedbackCardsProps {
  flags: Flag[] | undefined;
  hasData: boolean;
}

function metricIcon(metric: string): string {
  const m = metric.toLowerCase();
  if (m.includes("cadence") || m.includes("step")) return "👟";
  if (m.includes("knee")) return "🦵";
  if (m.includes("vertical") || m.includes("osc")) return "📏";
  if (m.includes("posture") || m.includes("torso") || m.includes("trunk")) return "🏃";
  if (m.includes("stride")) return "↔️";
  return "📊";
}

function computeScore(value: unknown, threshold: unknown): number {
  const v = Number(value);
  const t = Number(threshold);
  if (!isFinite(v) || !isFinite(t) || t === 0) return 50;
  if (v < t) return Math.round((v / t) * 100);
  if (v > t) return Math.round((t / v) * 100);
  return 100;
}

const FRIENDLY_LABELS: Record<string, string> = {
  cadence: "Cadence",
  vertical_oscillation: "Bounce",
  knee_flexion_at_strike: "Knee Drive",
  overstriding: "Overstriding",
  trunk_lean: "Posture",
  stride_and_cadence: "Stride & Cadence",
  cadence_confidence: "Cadence Confidence",
};

function humanLabel(metric: string): string {
  if (FRIENDLY_LABELS[metric]) return FRIENDLY_LABELS[metric];
  return metric
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function FeedbackCards({ flags, hasData }: FeedbackCardsProps) {
  if (!flags?.length) {
    if (!hasData) return null;
    return (
      <div className="bg-secondary border border-white/10 rounded-xl p-5 flex items-center gap-3">
        <span className="text-xl">✅</span>
        <div>
          <p className="text-sm font-medium text-white">Great form — no issues flagged</p>
          <p className="text-xs text-gray-400 mt-0.5">All metrics are within target ranges.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {flags.map((f, i) => {
        const score = computeScore(f.value, f.threshold);
        const isGood = score >= 90;
        const barColor = isGood ? "bg-primary" : score >= 65 ? "bg-amber-400" : "bg-red-500";
        const badge = isGood
          ? { label: "Good", classes: "bg-primary/15 text-primary border border-primary/30" }
          : { label: "Improve", classes: "bg-amber-400/15 text-amber-400 border border-amber-400/30" };

        return (
          <div
            key={i}
            className="bg-secondary border border-white/10 rounded-xl p-5 flex flex-col gap-3"
          >
            {/* Header row */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-lg leading-none">{metricIcon(f.metric)}</span>
                <span className="text-sm font-semibold text-white">{humanLabel(f.metric)}</span>
              </div>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full shrink-0 ${badge.classes}`}>
                {badge.label}
              </span>
            </div>

            {/* Score row */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-gray-400">Score</span>
                <span className="text-xs font-semibold text-white">{score}/100</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className={`h-full rounded-full ${barColor}`}
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>

            {/* Coach tip */}
            <div className="border-t border-white/10 pt-3">
              <p className="text-xs font-semibold tracking-widest text-primary uppercase mb-1">
                Coach Tip
              </p>
              <p className="text-xs text-gray-300 leading-relaxed">{f.recommendation}</p>
              {f.value != null && (
                <p className="text-xs text-gray-500 mt-1.5">
                  Current: {String(f.value)} · Target: {String(f.threshold)}
                </p>
              )}
            </div>

            {/* Drills */}
            {f.exercises && f.exercises.length > 0 && (
              <div className="border-t border-white/10 pt-3 space-y-2.5">
                <p className="text-xs font-semibold tracking-widest text-primary uppercase">
                  Drills to try
                </p>
                {f.exercises.map((ex) => (
                  <div key={ex.name}>
                    <p className="text-xs font-semibold text-white">{ex.name}</p>
                    <p className="text-xs text-gray-400 leading-relaxed mt-0.5">{ex.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

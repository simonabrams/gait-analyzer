import MetricTooltip from "@/components/MetricTooltip";
import { computeArcGeometry, RING_GOOD_COLOR, RING_WARN_COLOR } from "@/lib/arcRing";
import { METRIC_TARGETS } from "@/lib/metricTargets";

interface MetricCardsProps {
  summary: Record<string, unknown> | undefined;
}

const CONFIG = [
  {
    label: "CADENCE",
    key: METRIC_TARGETS.cadence.key,
    unit: METRIC_TARGETS.cadence.unit,
    tooltip:
      "Measured by detecting stride cycles in your video. Accurate to ±2–3% under good filming conditions. Best validated metric in video-based analysis.",
    disclaimer: null,
    good: METRIC_TARGETS.cadence.good,
    score: METRIC_TARGETS.cadence.score,
    blurb: (v: number) =>
      v >= 185
        ? "Excellent — high cadence, great efficiency"
        : v >= METRIC_TARGETS.cadence.target
        ? "Good — within the target range"
        : v >= 155
        ? "Below ideal — aim for 170–185 SPM"
        : "Well below target — aim for 170+ SPM",
  },
  {
    label: "BOUNCE",
    key: METRIC_TARGETS.bounce.key,
    unit: METRIC_TARGETS.bounce.unit,
    tooltip:
      "Estimated from vertical movement of torso landmarks. Compare this session-to-session rather than against your watch — wrist accelerometers and video use different measurement methods.",
    disclaimer: "Best compared session-to-session, not against wearables",
    good: METRIC_TARGETS.bounce.good,
    score: METRIC_TARGETS.bounce.score,
    blurb: (v: number) =>
      v <= 6
        ? "Excellent — minimal energy wasted"
        : v <= METRIC_TARGETS.bounce.target
        ? "Good — efficient, low bounce"
        : v <= 12
        ? "Slightly high — aim for under 10 cm"
        : "High bounce — too much up-and-down movement",
  },
  {
    label: "KNEE DRIVE",
    key: METRIC_TARGETS.kneeDrive.key,
    unit: METRIC_TARGETS.kneeDrive.unit,
    tooltip:
      "Joint angles from a single camera view are reliable within ~10% vs. lab-grade motion capture under optimal conditions. Accuracy drops with non-ideal camera angles.",
    disclaimer: "±~10% vs. lab-grade motion capture",
    good: METRIC_TARGETS.kneeDrive.good,
    score: METRIC_TARGETS.kneeDrive.score,
    blurb: (v: number) =>
      v >= 20
        ? "Excellent — strong knee drive at strike"
        : v >= METRIC_TARGETS.kneeDrive.target
        ? "Good — solid knee drive at foot strike"
        : v >= 10
        ? "Below ideal — aim for 15°+"
        : "Low knee drive — leg landing too straight",
  },
];

function ArcRing({
  score,
  isGood,
  value,
  unit,
}: {
  score: number;
  isGood: boolean;
  value: string;
  unit: string;
}) {
  const r = 36;
  const cx = 50;
  const cy = 50;
  const { circumference, arcLength, fillLength } = computeArcGeometry(r, score);
  const color = isGood ? RING_GOOD_COLOR : RING_WARN_COLOR;

  return (
    <div className="relative w-28 h-28 flex items-center justify-center">
      <svg viewBox="0 0 100 100" className="absolute inset-0 w-full h-full -rotate-[135deg]">
        {/* Background track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#2a2a2a"
          strokeWidth="8"
          strokeDasharray={`${arcLength} ${circumference - arcLength}`}
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={`${fillLength} ${circumference - fillLength}`}
          strokeLinecap="round"
        />
      </svg>
      <div className="relative text-center leading-tight">
        <span className="text-2xl font-bold text-white">{value}</span>
        <span className="block text-xs text-gray-400 mt-0.5">{unit}</span>
      </div>
    </div>
  );
}

export default function MetricCards({ summary }: MetricCardsProps) {
  if (!summary) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {CONFIG.map(({ label, key, unit, tooltip, disclaimer, good, score, blurb }) => {
        const raw = summary[key];
        const numVal = raw != null ? Number(raw) : null;
        const isGood = numVal != null ? good(numVal) : false;
        const scoreVal = numVal != null ? score(numVal) : 0;
        const display = numVal != null ? String(raw) : "—";
        const blurbText = numVal != null ? blurb(numVal) : null;

        return (
          <div
            key={key}
            className="bg-secondary border border-white/10 rounded-xl p-5 flex flex-col items-center gap-3"
          >
            <div className="flex items-center">
              <p className="text-xs font-semibold tracking-widest text-primary uppercase">
                {label}
              </p>
              <MetricTooltip content={tooltip} />
            </div>
            <ArcRing score={scoreVal} isGood={isGood} value={display} unit={unit} />
            {blurbText && (
              <p className="text-xs text-gray-400 text-center leading-snug">{blurbText}</p>
            )}
            {disclaimer && numVal != null && (
              <p className="text-[10px] text-gray-600 text-center leading-snug">{disclaimer}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

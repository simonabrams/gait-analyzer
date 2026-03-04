interface MetricCardsProps {
  summary: Record<string, unknown> | undefined;
}

const CONFIG = [
  { label: "Cadence", key: "cadence_avg", unit: "spm", target: "≥170" },
  { label: "Vertical Oscillation", key: "vertical_osc_avg_cm", unit: "cm", target: "≤10" },
  { label: "Knee Angle", key: "knee_angle_strike_avg_deg", unit: "°", target: "≥15" },
];

export default function MetricCards({ summary }: MetricCardsProps) {
  if (!summary) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {CONFIG.map(({ label, key, unit, target }) => {
        const val = summary[key];
        const display = val != null ? `${val} ${unit}` : "—";
        return (
          <div
            key={key}
            className="bg-white border rounded-lg p-4 shadow-sm"
          >
            <div className="text-sm text-gray-600">{label}</div>
            <div className="text-2xl font-semibold mt-1">{display}</div>
            <div className="text-xs text-gray-500 mt-1">Target: {target}</div>
          </div>
        );
      })}
    </div>
  );
}

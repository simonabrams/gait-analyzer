"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const AXIS_STYLE = { fill: "#9ca3af", fontSize: 11 };
const GRID_COLOR = "rgba(255,255,255,0.06)";
const TOOLTIP_STYLE = {
  background: "#1A1A1A",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "8px",
  color: "#fff",
  fontSize: 12,
};

interface StrideChartProps {
  title: string;
  strides: Array<Record<string, unknown>>;
  field: string;
  unit: string;
  /** True when a value is WITHIN target (dimmed); false = out of target
   * (full opacity). One predicate per metric, so an over-max metric (e.g.
   * foot strike) and an under-min metric (e.g. knee flexion) both correctly
   * highlight their bad bars — not just "low is bad" everywhere. */
  inTarget: (v: number) => boolean;
  targetBand: [number, number];
  targetLabel: string;
}

/** One bar-per-stride chart. Single color (not colored by left/right foot):
 * metrics.py's per-stride values are always one side's measurement
 * regardless of which foot's strikes bounded the stride — there's no real
 * per-foot split in this data today (see the plan for the full explanation),
 * so a left/right legend here would show a distinction that isn't real. */
function StrideChart({ title, strides, field, unit, inTarget, targetBand, targetLabel }: StrideChartProps) {
  const data = strides
    .map((s, i) => ({ stride: i + 1, value: s[field] }))
    .filter((d): d is { stride: number; value: number } => typeof d.value === "number");

  if (data.length === 0) return null;

  const outCount = data.filter((d) => !inTarget(d.value)).length;
  const avg = data.reduce((sum, d) => sum + d.value, 0) / data.length;
  const takeaway =
    outCount === 0
      ? `All ${data.length} strides within target (avg ${avg.toFixed(1)} ${unit}).`
      : `${outCount} of ${data.length} strides outside target — average ${avg.toFixed(1)} ${unit}.`;

  const yMax = Math.max(...data.map((d) => d.value), targetBand[1]) * 1.15;
  const yMin = Math.min(0, ...data.map((d) => d.value), targetBand[0]);

  return (
    <div className="bg-secondary border border-white/10 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-white mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
          <XAxis dataKey="stride" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
          <YAxis domain={[yMin, yMax]} tick={AXIS_STYLE} axisLine={false} tickLine={false} width={32} />
          <ReferenceArea
            y1={targetBand[0]}
            y2={targetBand[1]}
            fill="#00C896"
            fillOpacity={0.08}
            stroke="#00C896"
            strokeOpacity={0.4}
            strokeDasharray="4 4"
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            itemStyle={{ color: "#00C896" }}
            formatter={(v: number) => [`${v} ${unit}`, title]}
            labelFormatter={(l) => `Stride ${l}`}
          />
          <Bar dataKey="value" radius={[3, 3, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.stride} fill="#00C896" fillOpacity={inTarget(d.value) ? 0.45 : 1} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-400 mt-2">{takeaway}</p>
      <p className="text-[11px] text-gray-600 mt-1">Target {targetLabel}</p>
    </div>
  );
}

/** "SUPPORTING DETAIL" / "Stride by stride" — side-view only this pass. Rear
 * per-step charts need per-cycle data that doesn't exist in the schema yet
 * (rear_view only carries an aggregate median + one ensemble-averaged curve
 * per leg) — scoped out rather than fabricated; see the plan file. */
export default function StrideCharts({ strides }: { strides: Array<Record<string, unknown>> | undefined }) {
  if (!strides?.length) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <StrideChart
        title="Foot strike ahead of hip"
        strides={strides}
        field="foot_strike_position_cm"
        unit="cm"
        inTarget={(v) => v <= 10}
        targetBand={[0, 10]}
        targetLabel="≤10 cm"
      />
      <StrideChart
        title="Knee flexion at foot strike"
        strides={strides}
        field="knee_angle_strike_deg"
        unit="°"
        inTarget={(v) => v >= 15}
        targetBand={[15, 60]}
        targetLabel="≥15°"
      />
    </div>
  );
}

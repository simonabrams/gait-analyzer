"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { RunListItem } from "@/lib/api";

interface ProgressChartsProps {
  runs: RunListItem[];
}

function formatDate(created_at: string) {
  return new Date(created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

const AXIS_STYLE = { fill: "#9ca3af", fontSize: 11 };
const GRID_COLOR = "rgba(255,255,255,0.06)";
const REF_COLOR = "rgba(255,255,255,0.2)";

function ChartCard({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-secondary border border-white/10 rounded-xl p-5">
      <p className="text-xs font-semibold tracking-widest text-primary uppercase mb-0.5">
        {eyebrow}
      </p>
      <h3 className="text-sm font-semibold text-white mb-4">{title}</h3>
      {children}
    </div>
  );
}

export default function ProgressCharts({ runs }: ProgressChartsProps) {
  const data = runs
    .filter(
      (r) =>
        r.cadence_avg != null ||
        r.vertical_osc_avg_cm != null ||
        r.knee_angle_strike_avg_deg != null,
    )
    .map((r) => ({
      date: formatDate(r.created_at),
      fullDate: r.created_at,
      cadence: r.cadence_avg ?? undefined,
      verticalOsc: r.vertical_osc_avg_cm ?? undefined,
      kneeAngle: r.knee_angle_strike_avg_deg ?? undefined,
    }))
    .reverse();

  if (data.length === 0) return null;

  return (
    <div className="space-y-4">
      <ChartCard eyebrow="Progress" title="Cadence over time">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
            <XAxis dataKey="date" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={32} />
            <Tooltip
              contentStyle={{
                background: "#1A1A1A",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                color: "#fff",
                fontSize: 12,
              }}
              itemStyle={{ color: "#00C896" }}
            />
            <ReferenceLine y={170} stroke={REF_COLOR} strokeDasharray="4 4" />
            <Line
              type="monotone"
              dataKey="cadence"
              stroke="#00C896"
              strokeWidth={2}
              dot={{ r: 3, fill: "#00C896", strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard eyebrow="Progress" title="Bounce over time">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
            <XAxis dataKey="date" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={32} />
            <Tooltip
              contentStyle={{
                background: "#1A1A1A",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                color: "#fff",
                fontSize: 12,
              }}
              itemStyle={{ color: "#34d399" }}
            />
            <ReferenceLine y={10} stroke={REF_COLOR} strokeDasharray="4 4" />
            <Line
              type="monotone"
              dataKey="verticalOsc"
              stroke="#34d399"
              strokeWidth={2}
              dot={{ r: 3, fill: "#34d399", strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard eyebrow="Progress" title="Knee drive over time">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
            <XAxis dataKey="date" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={32} />
            <Tooltip
              contentStyle={{
                background: "#1A1A1A",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                color: "#fff",
                fontSize: 12,
              }}
              itemStyle={{ color: "#fbbf24" }}
            />
            <ReferenceLine y={15} stroke={REF_COLOR} strokeDasharray="4 4" />
            <Line
              type="monotone"
              dataKey="kneeAngle"
              stroke="#fbbf24"
              strokeWidth={2}
              dot={{ r: 3, fill: "#fbbf24", strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

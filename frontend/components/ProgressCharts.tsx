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

export default function ProgressCharts({ runs }: ProgressChartsProps) {
  const data = runs
    .filter((r) => r.cadence_avg != null || r.vertical_osc_avg_cm != null || r.knee_angle_strike_avg_deg != null)
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
    <div className="space-y-6">
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h3 className="font-medium mb-2">Cadence over time</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <ReferenceLine y={170} stroke="gray" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="cadence" stroke="#2563eb" strokeWidth={2} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h3 className="font-medium mb-2">Vertical oscillation over time</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <ReferenceLine y={10} stroke="gray" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="verticalOsc" stroke="#16a34a" strokeWidth={2} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h3 className="font-medium mb-2">Knee angle at foot strike over time</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <ReferenceLine y={15} stroke="gray" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="kneeAngle" stroke="#ca8a04" strokeWidth={2} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

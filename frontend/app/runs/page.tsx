"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listRuns, type RunListItem } from "@/lib/api";
import ProgressCharts from "@/components/ProgressCharts";

function formatDate(created_at: string) {
  return new Date(created_at).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export default function RunsPage() {
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRuns()
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-gray-600">Loading run history...</p>;
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Run history</h1>
        <Link href="/" className="text-blue-600 hover:underline">
          Upload new
        </Link>
      </div>

      <ProgressCharts runs={runs} />

      <div>
        <h2 className="text-lg font-semibold mb-3">Runs</h2>
        <div className="border rounded-lg overflow-hidden bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="text-left p-3">Date</th>
                <th className="text-left p-3">Cadence</th>
                <th className="text-left p-3">V. Oscillation</th>
                <th className="text-left p-3">Knee Angle</th>
                <th className="text-left p-3">Issues</th>
                <th className="text-left p-3">Link</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-gray-500">
                    No runs yet.
                  </td>
                </tr>
              ) : (
                runs.map((r) => (
                  <tr
                    key={r.run_id}
                    className="border-t hover:bg-gray-50 cursor-pointer"
                    onClick={() => window.location.assign(`/runs/${r.run_id}`)}
                  >
                    <td className="p-3">{formatDate(r.created_at)}</td>
                    <td className="p-3">{r.cadence_avg ?? "—"}</td>
                    <td className="p-3">{r.vertical_osc_avg_cm ?? "—"}</td>
                    <td className="p-3">{r.knee_angle_strike_avg_deg ?? "—"}</td>
                    <td className="p-3">{r.flags_count}</td>
                    <td className="p-3">
                      <Link
                        href={`/runs/${r.run_id}`}
                        className="text-blue-600 hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

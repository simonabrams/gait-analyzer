"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listRuns, deleteRun, type RunListItem, type RunListResponse } from "@/lib/api";

const PAGE_SIZE = 50;
import ProgressCharts from "@/components/ProgressCharts";

function formatDate(created_at: string) {
  return new Date(created_at).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  );
}

export default function RunsPage() {
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorId, setErrorId] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const loadRuns = (pageIndex: number) => {
    setLoading(true);
    listRuns({ limit: PAGE_SIZE, offset: pageIndex * PAGE_SIZE })
      .then((resp: RunListResponse) => {
        setRuns(resp.items);
        setTotal(resp.total);
      })
      .catch(() => { setRuns([]); setTotal(0); })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRuns(page);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleDelete = async (runId: string) => {
    setConfirmingId(null);
    setErrorId(null);
    setDeletingId(runId);
    const ok = await deleteRun(runId);
    setDeletingId(null);
    if (ok) {
      setRemovingId(runId);
      setTimeout(() => {
        setRuns((prev) => prev.filter((r) => r.run_id !== runId));
        setTotal((t) => t - 1);
        setRemovingId(null);
      }, 300);
    } else {
      setErrorId(runId);
    }
  };

  if (loading) {
    return <p className="text-gray-400">Loading run history...</p>;
  }

  if (!loading && total === 0) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Your Runs</h1>
          <p className="text-gray-400 mt-1">Track your progress over time — every run is saved here.</p>
        </div>
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <p className="text-5xl mb-4">🎥</p>
          <h2 className="text-xl font-semibold text-white mb-2">No runs yet</h2>
          <p className="text-gray-400 mb-6">Upload your first video to get started</p>
          <Link
            href="/#upload"
            className="bg-primary text-background font-medium px-6 py-3 rounded-lg hover:opacity-90 transition-opacity"
          >
            Analyze a Run →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Your Runs</h1>
        <p className="text-gray-400 mt-1">Track your progress over time — every run is saved here.</p>
      </div>

      <ProgressCharts runs={runs} />

      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Runs</h2>
        <div className="border border-white/10 rounded-lg overflow-hidden bg-secondary">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left p-3 text-gray-300 font-medium">Uploaded</th>
                <th className="text-left p-3 text-gray-300 font-medium">Recorded</th>
                <th className="text-left p-3 text-gray-300 font-medium">Cadence</th>
                <th className="text-left p-3 text-gray-300 font-medium">V. Oscillation</th>
                <th className="text-left p-3 text-gray-300 font-medium">Knee Angle</th>
                <th className="text-left p-3 text-gray-300 font-medium">Issues</th>
                <th className="text-left p-3 text-gray-300 font-medium">Link</th>
                <th className="text-left p-3 w-24" aria-label="Delete" />
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr
                  key={r.run_id}
                  className={`border-t border-white/5 hover:bg-white/5 cursor-pointer transition-opacity duration-300 ${
                    removingId === r.run_id ? "opacity-0" : ""
                  }`}
                  onClick={() => window.location.assign(`/runs/${r.run_id}`)}
                >
                  <td className="p-3 text-gray-300">{formatDate(r.created_at)}</td>
                  <td className="p-3 text-gray-300">{r.recorded_at ? formatDate(r.recorded_at) : "—"}</td>
                  <td className="p-3 text-gray-300">{r.cadence_avg ?? "—"}</td>
                  <td className="p-3 text-gray-300">{r.vertical_osc_avg_cm ?? "—"}</td>
                  <td className="p-3 text-gray-300">{r.knee_angle_strike_avg_deg ?? "—"}</td>
                  <td className="p-3 text-gray-300">{r.flags_count}</td>
                  <td className="p-3">
                    <Link
                      href={`/runs/${r.run_id}`}
                      className="text-primary hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View
                    </Link>
                  </td>
                  <td className="p-3" onClick={(e) => e.stopPropagation()}>
                    {errorId === r.run_id ? (
                      <span className="text-red-400 text-xs">Delete failed. Try again.</span>
                    ) : confirmingId === r.run_id ? (
                      <span className="flex gap-2">
                        <button
                          type="button"
                          className="text-gray-400 hover:text-white text-xs"
                          onClick={() => setConfirmingId(null)}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          className="text-red-400 hover:text-red-300 text-xs font-medium"
                          onClick={() => handleDelete(r.run_id)}
                        >
                          Yes, delete
                        </button>
                      </span>
                    ) : deletingId === r.run_id ? (
                      <span className="inline-block w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" aria-hidden />
                    ) : (
                      <button
                        type="button"
                        className="text-gray-400 hover:text-red-400 p-1"
                        onClick={() => setConfirmingId(r.run_id)}
                        aria-label="Delete run"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-between px-3 py-2 border-t border-white/10 text-sm text-gray-400">
              <span>
                {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1 rounded border border-white/10 disabled:opacity-40 hover:bg-white/5 transition-colors"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={(page + 1) * PAGE_SIZE >= total}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1 rounded border border-white/10 disabled:opacity-40 hover:bg-white/5 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

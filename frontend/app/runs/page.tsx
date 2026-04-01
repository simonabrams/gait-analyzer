"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
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

function SectionEyebrow({ label }: { label: string }) {
  return (
    <p className="text-xs font-semibold tracking-widest text-primary uppercase">{label}</p>
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
  const { getToken } = useAuth();

  const loadRuns = async (pageIndex: number) => {
    setLoading(true);
    try {
      const token = await getToken();
      const resp: RunListResponse = await listRuns(
        { limit: PAGE_SIZE, offset: pageIndex * PAGE_SIZE },
        token ?? undefined,
      );
      setRuns(resp.items);
      setTotal(resp.total);
    } catch {
      setRuns([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns(page);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleDelete = async (runId: string) => {
    setConfirmingId(null);
    setErrorId(null);
    setDeletingId(runId);
    const token = await getToken();
    const ok = await deleteRun(runId, token ?? "");
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
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="space-y-1 mb-8">
          <SectionEyebrow label="Run History" />
          <h1 className="text-3xl font-bold text-white">Your Runs</h1>
        </div>
        <div className="flex items-center gap-3 text-gray-400">
          <span className="inline-block w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" aria-hidden />
          Loading run history...
        </div>
      </div>
    );
  }

  if (!loading && total === 0) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        <div className="space-y-1">
          <SectionEyebrow label="Run History" />
          <h1 className="text-3xl font-bold text-white">Your Runs</h1>
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
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-10">

      {/* Page header */}
      <div className="space-y-1">
        <SectionEyebrow label="Run History" />
        <h1 className="text-3xl font-bold text-white">Your Runs</h1>
        <p className="text-sm text-gray-400">Track your progress over time — every run is saved here.</p>
      </div>

      {/* Progress charts */}
      <div className="space-y-4">
        <div>
          <SectionEyebrow label="Run Timeline" />
          <h2 className="text-xl font-semibold text-white mt-1">Metrics Over Time</h2>
        </div>
        <ProgressCharts runs={runs} />
      </div>

      {/* Runs table */}
      <div className="space-y-4">
        <div>
          <SectionEyebrow label="All Runs" />
          <h2 className="text-xl font-semibold text-white mt-1">Run Log</h2>
        </div>
        <div className="border border-white/10 rounded-xl overflow-hidden bg-secondary">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left px-4 py-3 text-xs font-semibold tracking-wider text-gray-400 uppercase">Uploaded</th>
                <th className="text-left px-4 py-3 text-xs font-semibold tracking-wider text-gray-400 uppercase">Recorded</th>
                <th className="text-left px-4 py-3 text-xs font-semibold tracking-wider text-gray-400 uppercase">Cadence</th>
                <th className="text-left px-4 py-3 text-xs font-semibold tracking-wider text-gray-400 uppercase">V. Osc.</th>
                <th className="text-left px-4 py-3 text-xs font-semibold tracking-wider text-gray-400 uppercase">Knee°</th>
                <th className="text-left px-4 py-3 text-xs font-semibold tracking-wider text-gray-400 uppercase">Issues</th>
                <th className="text-left px-4 py-3" />
                <th className="text-left px-4 py-3 w-24" aria-label="Delete" />
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
                  <td className="px-4 py-3 text-gray-300">{formatDate(r.created_at)}</td>
                  <td className="px-4 py-3 text-gray-400">{r.recorded_at ? formatDate(r.recorded_at) : "—"}</td>
                  <td className="px-4 py-3 font-medium text-white">{r.cadence_avg != null ? `${r.cadence_avg} spm` : "—"}</td>
                  <td className="px-4 py-3 font-medium text-white">{r.vertical_osc_avg_cm != null ? `${r.vertical_osc_avg_cm} cm` : "—"}</td>
                  <td className="px-4 py-3 font-medium text-white">{r.knee_angle_strike_avg_deg != null ? `${r.knee_angle_strike_avg_deg}°` : "—"}</td>
                  <td className="px-4 py-3">
                    {r.flags_count === 0 ? (
                      <span className="text-xs font-medium text-primary">✓ None</span>
                    ) : (
                      <span className="text-xs font-medium text-amber-400">{r.flags_count} flag{r.flags_count !== 1 ? "s" : ""}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/runs/${r.run_id}`}
                      className="text-xs font-medium text-primary hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View report →
                    </Link>
                  </td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
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
                        className="text-gray-500 hover:text-red-400 p-1 transition-colors"
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
            <div className="flex items-center justify-between px-4 py-3 border-t border-white/10 text-sm text-gray-400">
              <span>
                {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1 rounded-lg border border-white/10 disabled:opacity-40 hover:bg-white/5 transition-colors"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={(page + 1) * PAGE_SIZE >= total}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1 rounded-lg border border-white/10 disabled:opacity-40 hover:bg-white/5 transition-colors"
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

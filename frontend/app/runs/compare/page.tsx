"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { getRun, getBillingStatus, type RunDetail, type BillingStatus } from "@/lib/api";
import MetricCards from "@/components/MetricCards";
import ProUpsellTeaser from "@/components/ProUpsellTeaser";

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  return isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

const DELTA_METRICS = [
  { key: "cadence_avg", label: "Cadence", unit: "spm", higherIsBetter: true },
  { key: "vertical_osc_avg_cm", label: "Bounce", unit: "cm", higherIsBetter: false },
  { key: "knee_angle_strike_avg_deg", label: "Knee drive", unit: "°", higherIsBetter: true },
] as const;

function RunColumn({ run }: { run: RunDetail }) {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-gray-400">{formatDate(run.created_at)}</p>
      </div>
      <MetricCards summary={run.results?.summary} />
      {run.dashboard_image_url && (
        <div className="bg-secondary border border-white/10 rounded-xl overflow-hidden">
          <img src={run.dashboard_image_url} alt="Run dashboard" className="w-full h-auto" />
        </div>
      )}
    </div>
  );
}

export default function CompareRunsPage() {
  const searchParams = useSearchParams();
  const idA = searchParams.get("a");
  const idB = searchParams.get("b");
  const { getToken } = useAuth();

  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [runA, setRunA] = useState<RunDetail | null>(null);
  const [runB, setRunB] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!idA || !idB) {
      setError("Select two runs from your run history to compare.");
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const token = await getToken();
        const [status, a, b] = await Promise.all([
          token ? getBillingStatus(token) : Promise.resolve(null),
          getRun(idA),
          getRun(idB),
        ]);
        setBilling(status);
        setRunA(a);
        setRunB(b);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load runs");
      } finally {
        setLoading(false);
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idA, idB]);

  if (loading) {
    return <div className="max-w-6xl mx-auto px-4 py-8 text-gray-400">Loading…</div>;
  }

  if (error || !runA || !runB) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-4">
        <h1 className="text-2xl font-bold text-white">Compare runs</h1>
        <p className="text-red-400">{error ?? "Could not load runs."}</p>
        <Link href="/runs" className="text-primary hover:underline text-sm">
          Back to run history
        </Link>
      </div>
    );
  }

  if (!billing?.is_pro) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <ProUpsellTeaser
          title="Unlock run comparison with Pro"
          body="See two runs side by side with metric deltas — upgrade to Pro for unlimited scans and full comparison tools."
        />
      </div>
    );
  }

  const [older, newer] = new Date(runA.created_at) <= new Date(runB.created_at) ? [runA, runB] : [runB, runA];
  const summaryOlder = older.results?.summary ?? {};
  const summaryNewer = newer.results?.summary ?? {};

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Compare Runs</h1>
        <Link href="/runs" className="text-primary hover:underline text-sm">
          Back to run history
        </Link>
      </div>

      <div className="bg-secondary border border-white/10 rounded-xl p-5">
        <p className="text-xs font-semibold tracking-widest text-primary uppercase mb-3">
          Change from {formatDate(older.created_at)} to {formatDate(newer.created_at)}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {DELTA_METRICS.map(({ key, label, unit, higherIsBetter }) => {
            const oldVal = summaryOlder[key];
            const newVal = summaryNewer[key];
            if (oldVal == null || newVal == null) {
              return (
                <div key={key} className="text-sm text-gray-500">
                  {label}: —
                </div>
              );
            }
            const delta = Number(newVal) - Number(oldVal);
            const improved = higherIsBetter ? delta > 0 : delta < 0;
            const deltaColor = delta === 0 ? "text-gray-400" : improved ? "text-primary" : "text-amber-400";
            return (
              <div key={key}>
                <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
                <p className="text-sm text-white">
                  {String(oldVal)} → {String(newVal)} {unit}{" "}
                  <span className={deltaColor}>
                    ({delta > 0 ? "+" : ""}
                    {delta.toFixed(1)})
                  </span>
                </p>
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <RunColumn run={older} />
        <RunColumn run={newer} />
      </div>
    </div>
  );
}

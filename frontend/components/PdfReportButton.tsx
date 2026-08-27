"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import posthog from "posthog-js";
import { downloadRunReportPdf, ApiError } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

export default function PdfReportButton({ runId }: { runId: string }) {
  const { isSignedIn, getToken } = useAuth();
  const [working, setWorking] = useState(false);
  const [upgradeCode, setUpgradeCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isSignedIn) return null;

  const download = async () => {
    setWorking(true);
    setError(null);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      const blob = await downloadRunReportPdf(runId, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `runlens-report-${runId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      posthog.capture("pdf_report_downloaded");
    } catch (e) {
      if (e instanceof ApiError && e.code === "insufficient_data") {
        // Not a billing gate — the run doesn't have enough reliable data for
        // a PDF (see main.py's report.pdf endpoint). Plain message, not the
        // "upgrade to Pro" modal.
        setError(e.message || "This run doesn't have enough reliable data for a PDF report.");
      } else if (e instanceof ApiError && e.code) {
        setUpgradeCode(e.code);
      } else {
        setError(e instanceof Error ? e.message : "Could not generate PDF report");
      }
    } finally {
      setWorking(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={download}
        disabled={working}
        className="px-4 py-2 bg-secondary border border-white/20 hover:bg-white/10 rounded-lg text-sm font-medium text-gray-100 hover:text-white transition-colors disabled:opacity-60"
      >
        {working ? "Preparing…" : "Download PDF report"}
      </button>
      {error && <span className="text-red-400 text-xs ml-2">{error}</span>}
      {upgradeCode && (
        <UpgradeModal code={upgradeCode} source="pdf_export" onClose={() => setUpgradeCode(null)} />
      )}
    </>
  );
}

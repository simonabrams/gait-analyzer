"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import posthog from "posthog-js";
import { ApiError, downloadRunReportPdf } from "@/lib/api";

/** Download logic extracted from PdfReportButton so it can also be used from
 * ExportMenu's dropdown item — same behavior, two presentations. */
export function usePdfReport(runId: string) {
  const { isSignedIn, getToken } = useAuth();
  const [working, setWorking] = useState(false);
  const [upgradeCode, setUpgradeCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const download = async () => {
    if (!isSignedIn) return;
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

  return {
    isSignedIn,
    working,
    error,
    upgradeCode,
    dismissUpgrade: () => setUpgradeCode(null),
    download,
  };
}

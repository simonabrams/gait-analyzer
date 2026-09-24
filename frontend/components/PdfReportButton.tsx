"use client";

import { usePdfReport } from "@/lib/usePdfReport";
import UpgradeModal from "@/components/UpgradeModal";

export default function PdfReportButton({ runId }: { runId: string }) {
  const { isSignedIn, working, error, upgradeCode, dismissUpgrade, download } = usePdfReport(runId);

  if (!isSignedIn) return null;

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
        <UpgradeModal code={upgradeCode} source="pdf_export" onClose={dismissUpgrade} />
      )}
    </>
  );
}

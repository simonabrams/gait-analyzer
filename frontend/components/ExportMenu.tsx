"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import posthog from "posthog-js";
import { usePdfReport } from "@/lib/usePdfReport";
import UpgradeModal from "@/components/UpgradeModal";

/** "Export ▾" — groups the two less-frequent actions (Copy link, Download
 * PDF report) that used to be separate header buttons, leaving ShareButton
 * ("Share image") as the header's only primary action. */
export default function ExportMenu({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const pdf = usePdfReport(runId);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEscape);
    };
  }, [open]);

  const copyLink = useCallback(() => {
    if (typeof window === "undefined") return;
    navigator.clipboard.writeText(window.location.href).then(
      () => {
        setCopied(true);
        posthog.capture("share_link_copied");
        setTimeout(() => {
          setCopied(false);
          setOpen(false);
        }, 1200);
      },
      () => setCopied(false),
    );
  }, []);

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="px-4 py-2 bg-secondary border border-white/20 hover:bg-white/10 rounded-lg text-sm font-medium text-gray-100 hover:text-white transition-colors"
      >
        Export ▾
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-56 bg-secondary border border-white/10 rounded-lg shadow-xl overflow-hidden z-40"
        >
          <button
            type="button"
            role="menuitem"
            onClick={copyLink}
            className="w-full text-left px-4 py-2.5 text-sm text-gray-200 hover:bg-white/10 hover:text-white transition-colors"
          >
            {copied ? "Link copied!" : "Copy link"}
          </button>
          {pdf.isSignedIn && (
            <button
              type="button"
              role="menuitem"
              onClick={pdf.download}
              disabled={pdf.working}
              className="w-full text-left px-4 py-2.5 text-sm text-gray-200 hover:bg-white/10 hover:text-white transition-colors disabled:opacity-60 border-t border-white/5"
            >
              {pdf.working ? "Preparing…" : "Download PDF report"}
            </button>
          )}
          {pdf.error && (
            <p className="px-4 py-2 text-xs text-red-400 border-t border-white/5">{pdf.error}</p>
          )}
        </div>
      )}
      {pdf.upgradeCode && (
        <UpgradeModal code={pdf.upgradeCode} source="pdf_export" onClose={pdf.dismissUpgrade} />
      )}
    </div>
  );
}

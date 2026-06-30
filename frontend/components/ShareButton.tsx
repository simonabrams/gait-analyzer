"use client";

import { useState, useCallback } from "react";
import posthog from "posthog-js";

export default function ShareButton({ runId }: { runId: string }) {
  const [copied, setCopied] = useState(false);
  const [working, setWorking] = useState(false);

  const copyLink = useCallback(() => {
    if (typeof window === "undefined") return;
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        posthog.capture("share_link_copied");
      },
      () => setCopied(false)
    );
  }, []);

  const shareImage = useCallback(async () => {
    setWorking(true);
    try {
      const res = await fetch(`/runs/${runId}/share-card`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const file = new File([blob], "runlens-report.png", { type: "image/png" });

      if (typeof navigator.share === "function" && navigator.canShare?.({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: "My Runlens gait report",
          text: "Check out my running gait analysis from Runlens",
        });
        posthog.capture("share_image_downloaded", { method: "native_share" });
        return;
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "runlens-report.png";
      a.click();
      URL.revokeObjectURL(url);
      posthog.capture("share_image_downloaded", { method: "download" });
    } catch {
      // Share/download failed silently (e.g. user cancelled the share sheet)
    } finally {
      setWorking(false);
    }
  }, [runId]);

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={shareImage}
        disabled={working}
        className="px-4 py-2 bg-primary text-background rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-60"
      >
        {working ? "Preparing…" : "Share / Download image"}
      </button>
      <button
        type="button"
        onClick={copyLink}
        className="px-4 py-2 bg-secondary border border-white/20 hover:bg-white/10 rounded-lg text-sm font-medium text-gray-100 hover:text-white transition-colors"
      >
        {copied ? "Link copied!" : "Copy link"}
      </button>
    </div>
  );
}

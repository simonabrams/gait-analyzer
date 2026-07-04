"use client";

import { useEffect } from "react";
import posthog from "posthog-js";

const COPY: Record<string, { title: string; body: string; ctaLabel: string; ctaHref: string }> = {
  free_scan_used: {
    title: "You've used your free scan",
    body: "Upgrade to Pro for unlimited gait analyses, progress tracking over time, and more — with a 7-day free trial.",
    ctaLabel: "See Pro plans",
    ctaHref: "/pricing",
  },
  subscription_inactive: {
    title: "Your Pro subscription is inactive",
    body: "There was a problem with your last payment. Update your payment method to keep unlimited access.",
    ctaLabel: "Update payment method",
    ctaHref: "/account/billing",
  },
};

const DEFAULT_COPY = {
  title: "Upgrade to Pro",
  body: "This feature is available on the Pro plan.",
  ctaLabel: "See Pro plans",
  ctaHref: "/pricing",
};

export default function UpgradeModal({
  code,
  source,
  onClose,
}: {
  code: string;
  source: string;
  onClose: () => void;
}) {
  const copy = COPY[code] ?? DEFAULT_COPY;

  useEffect(() => {
    posthog.capture("upgrade_prompt_shown", { code, source });
  }, [code, source]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      onClick={onClose}
    >
      <div
        className="bg-secondary border border-white/10 rounded-2xl p-8 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold text-white mb-3">{copy.title}</h2>
        <p className="text-gray-300 text-sm mb-6">{copy.body}</p>
        <div className="flex gap-3">
          <a
            href={copy.ctaHref}
            className="flex-1 text-center py-3 bg-primary text-background font-semibold rounded-lg hover:opacity-90 transition-opacity"
          >
            {copy.ctaLabel}
          </a>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-3 text-gray-400 hover:text-white transition-colors text-sm"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}

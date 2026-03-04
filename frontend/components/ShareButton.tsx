"use client";

import { useState, useCallback } from "react";

export default function ShareButton() {
  const [copied, setCopied] = useState(false);

  const copyLink = useCallback(() => {
    if (typeof window === "undefined") return;
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => setCopied(false)
    );
  }, []);

  return (
    <button
      type="button"
      onClick={copyLink}
      className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-sm font-medium transition-colors"
    >
      {copied ? "Link copied!" : "Copy shareable link"}
    </button>
  );
}

"use client";

import { useState } from "react";

export default function TechAccordion() {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-primary hover:opacity-80 font-medium transition-opacity"
      >
        <span className="text-xs">{open ? "▼" : "▶"}</span> Tech stack
      </button>
      {open && (
        <p className="mt-3 text-gray-400 text-sm leading-relaxed">
          Runlens is built with Next.js, FastAPI, MediaPipe, and Cloudflare R2. It runs on
          Render and Vercel.
        </p>
      )}
    </div>
  );
}

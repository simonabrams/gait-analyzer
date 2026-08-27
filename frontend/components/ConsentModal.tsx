"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import posthog from "posthog-js";

/** Copy is drafted in docs/trust/03-in-app-copy.md §1 — pending legal review.
 * The checkbox sentence is the load-bearing consent language; don't edit it
 * without updating the doc (and counsel sign-off).
 *
 * The "I'm 18 or older" checkbox is required of every user, signed in or
 * not — nothing upstream of this (Clerk sign-up included) establishes age
 * today. The backend enforces this too (see main.py's accept_consent), this
 * is UX, not the security boundary. */
export default function ConsentModal({
  onAgree,
  onClose,
  busy,
  error,
}: {
  onAgree: (ageConfirmed: boolean) => void;
  onClose: () => void;
  busy: boolean;
  error: string | null;
}) {
  const [checked, setChecked] = useState(false);
  const [ageChecked, setAgeChecked] = useState(false);
  const canContinue = checked && ageChecked;

  useEffect(() => {
    posthog.capture("consent_prompt_shown");
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      onClick={busy ? undefined : onClose}
    >
      <div
        className="bg-secondary border border-white/10 rounded-2xl p-8 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold text-white mb-3">Before your first analysis</h2>
        <p className="text-gray-300 text-sm mb-3 leading-relaxed">
          To analyze your form, Runlens uploads your video to our servers, where a
          computer-vision model measures your movement — cadence, joint angles, stride.
          Your video and results stay with us until you delete them, and deleting a
          run removes them from our storage.
        </p>
        <p className="text-gray-300 text-sm mb-5 leading-relaxed">
          We never sell your data or use your video to train AI.
        </p>
        <label className="flex items-start gap-3 mb-6 cursor-pointer">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            className="mt-0.5 h-4 w-4 accent-primary"
          />
          <span className="text-gray-300 text-sm leading-relaxed">
            I&apos;ve read and agree to the{" "}
            <Link href="/privacy" target="_blank" className="text-primary hover:underline">
              Privacy Policy
            </Link>{" "}
            and{" "}
            <Link href="/terms" target="_blank" className="text-primary hover:underline">
              Terms
            </Link>
            , and I consent to Runlens processing my video and the body-movement
            measurements derived from it.
          </span>
        </label>
        <label className="flex items-start gap-3 mb-6 cursor-pointer">
          <input
            type="checkbox"
            checked={ageChecked}
            onChange={(e) => setAgeChecked(e.target.checked)}
            className="mt-0.5 h-4 w-4 accent-primary"
          />
          <span className="text-gray-300 text-sm leading-relaxed">
            I&apos;m 18 or older.
          </span>
        </label>
        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => onAgree(ageChecked)}
            disabled={!canContinue || busy}
            className="flex-1 py-3 bg-primary text-background font-semibold rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {busy ? "Saving…" : "Agree & continue"}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="px-4 py-3 text-gray-400 hover:text-white transition-colors text-sm"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}

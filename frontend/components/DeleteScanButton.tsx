"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import posthog from "posthog-js";
import { deleteRun } from "@/lib/api";
import { getStoredAnonId, hasAnonRun, forgetAnonRun } from "@/lib/anon";

/** Self-serve deletion for a scan made without an account. Anonymous visitors
 * have no /runs history to delete from, so this is the only place they can
 * remove their data themselves — see docs/trust/00-trust-principles.md #2
 * ("you can delete your video and results — anytime").
 *
 * Only renders for the browser that actually created this run anonymously
 * (tracked in localStorage — see lib/anon.ts), so it never appears for other
 * visitors viewing a shared run link, and never for signed-in users (their
 * runs are deleted from the Runs page instead). */
export default function DeleteScanButton({ runId }: { runId: string }) {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(false);
  const [done, setDone] = useState(false);

  // Wait for Clerk to resolve, then only ever show this to an anonymous
  // visitor whose browser remembers creating this specific run.
  if (!isLoaded || isSignedIn || !hasAnonRun(runId)) return null;

  const handleDelete = async () => {
    setError(false);
    setDeleting(true);
    const anonId = getStoredAnonId() ?? undefined;
    const ok = await deleteRun(runId, undefined, anonId);
    setDeleting(false);
    if (ok) {
      forgetAnonRun(runId);
      posthog.capture("anon_run_deleted");
      setDone(true);
      setTimeout(() => router.push("/"), 1500);
    } else {
      setError(true);
    }
  };

  if (done) {
    return <p className="text-sm text-primary">Scan deleted. Taking you home…</p>;
  }

  if (confirming) {
    return (
      <span className="flex items-center gap-2 text-sm">
        <span className="text-gray-400">Delete this scan?</span>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="text-red-400 hover:text-red-300 font-medium disabled:opacity-60"
        >
          {deleting ? "Deleting…" : "Confirm"}
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          disabled={deleting}
          className="text-gray-400 hover:text-white"
        >
          Cancel
        </button>
      </span>
    );
  }

  return (
    <span className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="px-4 py-2 bg-secondary border border-white/20 hover:bg-red-400/10 hover:border-red-400/40 rounded-lg text-sm font-medium text-gray-300 hover:text-red-300 transition-colors"
      >
        Delete this scan
      </button>
      {error && <span className="text-red-400 text-xs">Couldn&apos;t delete — try again.</span>}
    </span>
  );
}

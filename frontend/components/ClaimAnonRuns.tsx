"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { claimAnonymousRuns } from "@/lib/api";
import { clearAnonId, getStoredAnonId } from "@/lib/anon";

/** Invisible; mounted once in the root layout so it fires regardless of which
 * page a sign-up completes on. Merges any anonymous run(s)/consent/free-scan
 * usage into the now-signed-in account. Safe to re-run — the backend claim
 * endpoint is idempotent. */
export default function ClaimAnonRuns() {
  const { isSignedIn, getToken } = useAuth();

  useEffect(() => {
    if (!isSignedIn) return;
    const anonId = getStoredAnonId();
    if (!anonId) return;
    (async () => {
      const token = await getToken();
      if (!token) return;
      try {
        await claimAnonymousRuns(anonId, token);
        clearAnonId();
      } catch {
        // Leave the anon id in place — retried on the next sign-in.
      }
    })();
  }, [isSignedIn, getToken]);

  return null;
}

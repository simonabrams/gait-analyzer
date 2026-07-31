"use client";

import { useEffect, useState } from "react";
import { useAuth, SignUpButton } from "@clerk/nextjs";
import posthog from "posthog-js";

/** Non-blocking nudge shown on a just-created run's results page, prompting
 * the anonymous visitor who created it to sign up and save it. Only relevant
 * right after upload (see `?justCreated=1` in the redirect from HomeClient),
 * not for arbitrary public viewers of a shared run link. */
export default function ClaimBanner({ show }: { show: boolean }) {
  const { isSignedIn } = useAuth();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (show && !isSignedIn) posthog.capture("signup_banner_shown");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!show || isSignedIn || dismissed) return null;

  return (
    <div className="rounded-xl border border-primary/30 bg-primary/10 px-5 py-4 flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-gray-200">
        Create a free account to save this result and track your progress over time.
      </p>
      <div className="flex items-center gap-3">
        <SignUpButton mode="modal">
          <button
            type="button"
            onClick={() => posthog.capture("signup_banner_clicked")}
            className="px-4 py-2 bg-primary text-background font-semibold text-sm rounded-lg hover:opacity-90 transition-opacity"
          >
            Save my results
          </button>
        </SignUpButton>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
          className="text-gray-400 hover:text-white transition-colors text-lg leading-none"
        >
          ×
        </button>
      </div>
    </div>
  );
}

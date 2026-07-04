"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import posthog from "posthog-js";
import { getBillingStatus, createPortalSession, BillingStatus } from "@/lib/api";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

const STATUS_LABELS: Record<string, string> = {
  trialing: "Trialing",
  active: "Active",
  past_due: "Payment failed — please update your card",
  canceled: "Canceled",
  grandfathered: "Complimentary Pro (early access)",
};

export default function AccountBillingPage() {
  const { getToken } = useAuth();
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      setBilling(await getBillingStatus(token));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load billing status");
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    load();
  }, [load]);

  const openPortal = async () => {
    setPortalLoading(true);
    posthog.capture("portal_opened");
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      const { url } = await createPortalSession(token);
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open billing portal");
      setPortalLoading(false);
    }
  };

  const copyReferralLink = () => {
    if (!billing) return;
    navigator.clipboard.writeText(billing.referral_link).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loading) {
    return <div className="max-w-2xl mx-auto px-6 py-20 text-gray-400">Loading…</div>;
  }

  if (error || !billing) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-20 text-red-400">
        {error || "Could not load billing status."}
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-20 space-y-8">
      <div>
        <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-3">
          Account
        </p>
        <h1 className="text-3xl font-bold text-white">Billing</h1>
      </div>

      <div className="bg-secondary border border-white/10 rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-400">Current plan</p>
            <p className="text-xl font-semibold text-white capitalize">
              {billing.tier}
              {billing.status && (
                <span className="ml-2 text-sm font-normal text-gray-400">
                  ({STATUS_LABELS[billing.status] ?? billing.status})
                </span>
              )}
            </p>
          </div>
          {!billing.is_pro && (
            <a
              href="/pricing"
              className="bg-primary text-background text-sm font-semibold px-4 py-2 rounded-lg hover:opacity-90 transition-opacity"
            >
              Upgrade to Pro
            </a>
          )}
        </div>

        {billing.tier === "free" && (
          <p className="text-sm text-gray-300">
            Free scans used: {billing.free_scans_used} / {billing.free_scans_limit + billing.bonus_scans}
          </p>
        )}
        {billing.trial_end && (
          <p className="text-sm text-gray-300">Trial ends: {formatDate(billing.trial_end)}</p>
        )}
        {billing.current_period_end && (
          <p className="text-sm text-gray-300">
            {billing.cancel_at_period_end ? "Access ends" : "Renews"}: {formatDate(billing.current_period_end)}
          </p>
        )}

        {billing.tier === "pro" && (
          <button
            type="button"
            onClick={openPortal}
            disabled={portalLoading}
            className="w-full py-3 bg-white/10 text-white font-semibold rounded-lg hover:bg-white/20 disabled:opacity-50 transition-colors"
          >
            {portalLoading ? "Opening…" : "Manage billing"}
          </button>
        )}
      </div>

      <div className="bg-secondary border border-white/10 rounded-2xl p-6 space-y-3">
        <p className="text-sm text-gray-400">Refer a friend</p>
        <p className="text-sm text-gray-300">
          Share your link — when a friend completes their first analysis, you both get a bonus
          free scan.
        </p>
        <div className="flex gap-2">
          <input
            readOnly
            value={billing.referral_link}
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200"
          />
          <button
            type="button"
            onClick={copyReferralLink}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-medium text-white transition-colors"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
        <p className="text-xs text-gray-500">Bonus scans earned: {billing.bonus_scans}</p>
      </div>
    </div>
  );
}

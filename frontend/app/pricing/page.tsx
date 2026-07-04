"use client";

import { useState } from "react";
import { useAuth, useClerk } from "@clerk/nextjs";
import posthog from "posthog-js";
import PricingCard from "@/components/PricingCard";
import { createCheckoutSession } from "@/lib/api";

export default function PricingPage() {
  const { isSignedIn, getToken } = useAuth();
  const { openSignIn } = useClerk();
  const [loadingPlan, setLoadingPlan] = useState<"monthly" | "yearly" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startCheckout = async (plan: "monthly" | "yearly") => {
    if (!isSignedIn) {
      openSignIn();
      return;
    }
    setError(null);
    setLoadingPlan(plan);
    posthog.capture("checkout_started", { plan });
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      const { url } = await createCheckoutSession(plan, token);
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start checkout");
      setLoadingPlan(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-20">
      <div className="text-center mb-14">
        <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-3">Pricing</p>
        <h1 className="text-4xl font-bold text-white mb-4">Simple, honest pricing</h1>
        <p className="text-gray-400 max-w-xl mx-auto">
          Your first gait analysis is free. Upgrade to Pro for unlimited scans and progress
          tracking over time.
        </p>
      </div>

      {error && <p className="text-center text-red-400 text-sm mb-6">{error}</p>}

      <div className="grid md:grid-cols-3 gap-6">
        <PricingCard
          name="Free"
          price="$0"
          description="Try Runlens with one full analysis, on us."
          features={[
            "1 gait analysis",
            "Annotated video + dashboard",
            "Personalized drill recommendations",
          ]}
          ctaLabel="Get started"
          onSelect={() => {
            window.location.href = "/#upload";
          }}
        />
        <PricingCard
          name="Pro Monthly"
          price="$9.99"
          period="mo"
          badge="7-day free trial"
          description="Unlimited scans, billed monthly."
          features={[
            "Unlimited gait analyses",
            "Progress tracking over time",
            "Run comparison view",
            "Branded PDF report export",
            "Cancel anytime",
          ]}
          ctaLabel={loadingPlan === "monthly" ? "Redirecting…" : "Start 7-day free trial"}
          disabled={loadingPlan !== null}
          onSelect={() => startCheckout("monthly")}
        />
        <PricingCard
          highlighted
          name="Pro Yearly"
          price="$59.99"
          period="yr"
          badge="Best value — save 50%"
          description="Unlimited scans, billed annually."
          features={["Everything in Pro Monthly", "Save ~50% vs. monthly", "7-day free trial"]}
          ctaLabel={loadingPlan === "yearly" ? "Redirecting…" : "Start 7-day free trial"}
          disabled={loadingPlan !== null}
          onSelect={() => startCheckout("yearly")}
        />
      </div>

      <p className="text-center text-gray-500 text-xs mt-10">
        A card is required to start your trial. You won&apos;t be charged until the trial ends,
        and you can cancel anytime from your billing settings.
      </p>
    </div>
  );
}

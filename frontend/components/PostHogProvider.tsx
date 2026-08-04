"use client";

import posthog from "posthog-js";
import { PostHogProvider as PHProvider } from "posthog-js/react";
import { useEffect, Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { useUser } from "@clerk/nextjs";

function PostHogPageview() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (pathname) {
      const url =
        window.origin +
        pathname +
        (searchParams.toString() ? `?${searchParams.toString()}` : "");
      posthog.capture("$pageview", { $current_url: url });
    }
  }, [pathname, searchParams]);

  return null;
}

function UserIdentifier() {
  const { user } = useUser();

  useEffect(() => {
    if (user) {
      posthog.identify(user.id);
    }
  }, [user]);

  return null;
}

export default function PostHogProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host:
        process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
      capture_pageview: false,
      // Pageviews are captured manually (see PostHogPageview below) since we're
      // on the App Router, so $pageleave needs to be opted in explicitly too —
      // it defaults to mirroring capture_pageview otherwise.
      capture_pageleave: true,
    });
  }, []);

  return (
    <PHProvider client={posthog}>
      <Suspense fallback={null}>
        <PostHogPageview />
      </Suspense>
      <UserIdentifier />
      {children}
    </PHProvider>
  );
}

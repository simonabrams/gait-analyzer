import type { Metadata } from "next";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import Nav from "@/components/Nav";
import PostHogProvider from "@/components/PostHogProvider";
import ClaimAnonRuns from "@/components/ClaimAnonRuns";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? "https://runlens.io"),
  title: {
    default: "Runlens.io",
    template: "%s — Runlens",
  },
  description: "AI-powered running gait analysis. Upload a video, get instant form feedback.",
  openGraph: {
    siteName: "Runlens",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    site: "@runlens",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="antialiased min-h-screen bg-background text-gray-100 font-sans">
          <PostHogProvider>
            <ClaimAnonRuns />
            <Nav />
            <main className="pt-14 min-h-screen">
              {children}
            </main>
            <Analytics />
            <SpeedInsights />
          </PostHogProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}

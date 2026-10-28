import type { Metadata } from "next";
import HomeClient from "@/components/HomeClient";

export const metadata: Metadata = {
  title: {
    absolute: "Runlens — AI-Powered Running Gait Analysis",
  },
  description:
    "Upload a short side-view running video, plus an optional rear view, and get AI feedback on your cadence, bounce, knee drive and left/right balance. Free to try.",
  openGraph: {
    title: "Runlens — AI-Powered Running Gait Analysis",
    description:
      "Upload a short side-view running video, plus an optional rear view, and get AI feedback on your cadence, bounce, knee drive and left/right balance.",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Runlens",
  applicationCategory: "HealthApplication",
  operatingSystem: "Web",
  description:
    "AI-powered running gait analysis. Upload a side-view video (and optionally one from behind) and get form feedback on cadence, stride, posture and left/right balance.",
  url: "https://runlens.io",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <HomeClient />
    </>
  );
}

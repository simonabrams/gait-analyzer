import type { Metadata } from "next";
import HomeClient from "@/components/HomeClient";

export const metadata: Metadata = {
  title: {
    absolute: "Runlens — AI-Powered Running Gait Analysis",
  },
  description:
    "Upload a short side-view running video and get instant AI feedback on your cadence, vertical oscillation, knee angle, and overall running form. Free to try.",
  openGraph: {
    title: "Runlens — AI-Powered Running Gait Analysis",
    description:
      "Upload a short side-view running video and get instant AI feedback on your cadence, vertical oscillation, knee angle, and overall running form.",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Runlens",
  applicationCategory: "HealthApplication",
  operatingSystem: "Web",
  description:
    "AI-powered running gait analysis. Upload a video, get instant form feedback on cadence, stride, posture, and more.",
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

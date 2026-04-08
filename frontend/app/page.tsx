"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import VideoUploader from "@/components/VideoUploader";
import { listRuns, SAMPLE_RUN_ID } from "@/lib/api";
import Footer from "@/components/Footer";

export default function HomePage() {
  const router = useRouter();
  const [hasRuns, setHasRuns] = useState(false);

  useEffect(() => {
    listRuns()
      .then((r) => setHasRuns(r.total > 0))
      .catch(() => setHasRuns(false));
  }, []);

  const handleComplete = (runId: string) => {
    router.push(`/runs/${runId}`);
  };

  return (
    <div>
      {/* Hero */}
      <section
        className="min-h-screen flex flex-col justify-center py-24 relative overflow-hidden"
        style={{
          backgroundImage: "url(/images/hero-bg.jpg)",
          backgroundSize: "cover",
          backgroundPosition: "center top",
        }}
      >
        <div className="absolute inset-0 bg-black/55" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20" />

        <div className="relative z-10 text-center max-w-3xl mx-auto px-6">
          <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-5">
            AI-Powered Gait Analysis
          </p>
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white leading-tight">
            See your run.
          </h1>
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-primary leading-tight mb-6">
            Improve your form.
          </h1>
          <p className="text-lg text-gray-300 mb-10 max-w-xl mx-auto leading-relaxed">
            Upload a short video and get instant, visual feedback on your running gait —
            cadence, stride, posture, and more.
          </p>
          <div className="flex flex-wrap gap-4 justify-center mb-12">
            <Link
              href="/#upload"
              className="bg-primary text-background font-semibold px-8 py-3.5 rounded-lg hover:opacity-90 transition-opacity"
            >
              Analyze a Run →
            </Link>
            <Link
              href={`/runs/${SAMPLE_RUN_ID}`}
              className="border border-white/40 text-white font-medium px-8 py-3.5 rounded-lg hover:border-white hover:bg-white/5 transition-colors"
            >
              See a Sample Report
            </Link>
          </div>
          <div className="flex flex-wrap gap-6 justify-center text-sm text-gray-300">
            <span className="flex items-center gap-2">
              <span className="text-base">📹</span> Upload any video
            </span>
            <span className="text-gray-600">·</span>
            <span className="flex items-center gap-2">
              <span className="text-base">⚡</span> Results in ~60s
            </span>
            <span className="text-gray-600">·</span>
            <span className="flex items-center gap-2">
              <span className="text-base">📈</span> Track progress over time
            </span>
          </div>
        </div>
      </section>

      {/* Upload */}
      <section id="upload" className="py-20 scroll-mt-20 bg-background">
        <div className="max-w-lg mx-auto px-4">
          <h2 className="text-3xl font-bold text-white mb-2 text-center">
            Ready to analyze your run?
          </h2>
          <p className="text-gray-400 text-center mb-8">
            Drop in a video and we&apos;ll handle the rest.
          </p>
          <div
            className="rounded-2xl overflow-hidden border border-white/10 relative"
            // style={{
            //   backgroundImage: "url(https://picsum.photos/seed/treadmill-run/800/600)",
            //   backgroundSize: "cover",
            //   backgroundPosition: "center",
            // }}
          >
            <div className="absolute inset-0 bg-black/70" />
            <div className="relative z-10 p-7">
              <VideoUploader onComplete={handleComplete} />
            </div>
          </div>
          <p className="mt-5 text-sm text-gray-500 text-center">
            💡 Best results: film from the side, full body visible, 30–60 seconds of steady
            running on a treadmill
          </p>
          {hasRuns && (
            <p className="mt-3 text-center">
              <Link href="/runs" className="text-primary hover:underline text-sm">
                ← View your previous runs
              </Link>
            </p>
          )}
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 bg-background">
        <div className="max-w-5xl mx-auto px-4">
          <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase text-center mb-3">
            The Process
          </p>
          <h2 className="text-3xl font-bold text-white mb-12 text-center">How it works</h2>
          <div className="grid md:grid-cols-3 gap-5">
            {[
              {
                seed: "athlete-running",
                icon: "🎥",
                title: "Film your run",
                desc: "30–60 seconds from the side, on a treadmill. Your phone works great.",
              },
              {
                seed: "smartphone-upload",
                icon: "⬆️",
                title: "Upload your video",
                desc: "Drop it in and tell us your height. That's all we need.",
              },
              {
                seed: "data-analytics",
                icon: "📊",
                title: "Get your analysis",
                desc: "See your cadence, stride, posture — and what to work on next.",
              },
            ].map(({ seed, icon, title, desc }) => (
              <div
                key={seed}
                className="rounded-2xl overflow-hidden relative h-64"
                style={{
                  backgroundImage: `url(https://picsum.photos/seed/${seed}/600/400)`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                }}
              >
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent" />
                <div className="absolute inset-0 p-6 flex flex-col justify-end">
                  <span className="text-2xl mb-2">{icon}</span>
                  <h3 className="font-semibold text-white text-lg mb-1">{title}</h3>
                  <p className="text-gray-300 text-sm leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonial */}
      <section
        className="py-28 relative overflow-hidden"
        style={{
          backgroundImage: "url(/images/testimonial-bg.jpg)",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0 bg-black/75" />
        <div className="relative z-10 max-w-3xl mx-auto px-6 text-center">
          <blockquote className="text-2xl md:text-3xl font-medium text-white leading-relaxed italic">
            &ldquo;Finally an app that tells me{" "}
            <span className="text-primary not-italic font-semibold">why</span>{" "}
            my knee hurts — not just that it does.&rdquo;
          </blockquote>
          <p className="mt-6 text-xs font-semibold tracking-[0.2em] uppercase text-gray-400">
            — Marathon Runner, Berlin
          </p>
        </div>
      </section>

      <Footer />
    </div>
  );
}

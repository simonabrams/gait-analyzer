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
      .then((r) => setHasRuns(r.length > 0))
      .catch(() => setHasRuns(false));
  }, []);

  const handleComplete = (runId: string) => {
    router.push(`/runs/${runId}`);
  };

  return (
    <div>
      <section className="min-h-screen flex flex-col justify-center py-20 relative overflow-hidden">
        <div className="absolute inset-0 bg-background bg-[linear-gradient(180deg,rgba(0,200,150,0.03)_0%,transparent_50%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(26,26,26,0.5)_1px,transparent_1px),linear-gradient(rgba(26,26,26,0.5)_1px,transparent_1px)] bg-[size:48px_48px]" />
        <div className="relative z-10 text-center max-w-2xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            See your run. Improve your form.
          </h1>
          <p className="text-lg text-gray-300 mb-8">
            Upload a short video and get instant, visual feedback on your running gait — cadence, stride, posture, and more.
          </p>
          <div className="flex flex-wrap gap-4 justify-center mb-10">
            <Link
              href="/#upload"
              className="bg-primary text-background font-medium px-6 py-3 rounded-lg hover:opacity-90 transition-opacity"
            >
              Analyze a Run →
            </Link>
            <Link
              href={`/runs/${SAMPLE_RUN_ID}`}
              className="border border-gray-500 text-gray-200 font-medium px-6 py-3 rounded-lg hover:border-primary hover:text-primary transition-colors"
            >
              See a Sample Report
            </Link>
          </div>
          <div className="flex flex-wrap gap-4 justify-center text-sm text-gray-400">
            <span className="bg-secondary/80 px-4 py-2 rounded-full">📹 Upload any video</span>
            <span className="bg-secondary/80 px-4 py-2 rounded-full">⚡ Results in ~60s</span>
            <span className="bg-secondary/80 px-4 py-2 rounded-full">📈 Track progress over time</span>
          </div>
        </div>
      </section>

      <section id="upload" className="py-16 scroll-mt-20">
        <div className="max-w-xl mx-auto">
          <h2 className="text-2xl font-semibold text-white mb-6 text-center">
            Ready to analyze your run?
          </h2>
          <div className="bg-secondary rounded-xl p-6 border border-white/10">
            <VideoUploader onComplete={handleComplete} />
          </div>
          <p className="mt-4 text-sm text-gray-400 text-center">
            💡 Best results: film from the side, full body visible, 30–60 seconds of steady running on a treadmill
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

      <section className="py-16">
        <h2 className="text-2xl font-semibold text-white mb-8 text-center">How it works</h2>
        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          <div className="bg-secondary rounded-xl p-6 border border-white/10">
            <p className="text-2xl mb-2">🎥</p>
            <h3 className="font-semibold text-white mb-2">Film your run</h3>
            <p className="text-gray-400 text-sm">30–60 seconds from the side, on a treadmill. Your phone works great.</p>
          </div>
          <div className="bg-secondary rounded-xl p-6 border border-white/10">
            <p className="text-2xl mb-2">⬆️</p>
            <h3 className="font-semibold text-white mb-2">Upload your video</h3>
            <p className="text-gray-400 text-sm">Drop it in and tell us your height. That&apos;s all we need.</p>
          </div>
          <div className="bg-secondary rounded-xl p-6 border border-white/10">
            <p className="text-2xl mb-2">📊</p>
            <h3 className="font-semibold text-white mb-2">Get your analysis</h3>
            <p className="text-gray-400 text-sm">See your cadence, stride, posture — and what to work on next.</p>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}

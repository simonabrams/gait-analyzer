"use client";

import { useState } from "react";
import Footer from "@/components/Footer";

const METRICS = [
  { metric: "Cadence", target: "170–180 spm", meaning: "Steps per minute" },
  { metric: "Vertical oscill.", target: "< 10 cm", meaning: "How much you bounce" },
  { metric: "Knee flexion", target: "> 15°", meaning: "Shock absorption at impact" },
  { metric: "Trunk lean", target: "< 15°", meaning: "Forward body angle" },
  { metric: "Overstriding", target: "< 10 cm ahead", meaning: "Foot landing vs. hips" },
];

export default function AboutPage() {
  const [techOpen, setTechOpen] = useState(false);

  return (
    <div className="py-8 max-w-3xl mx-auto">
      <section className="mb-12">
        <h1 className="text-3xl font-bold text-white mb-4">Built by a runner, for runners.</h1>
        <p className="text-gray-300 leading-relaxed">
          Runlens is a simple tool that helps you see what’s going on with your running form. Upload a short video from the side, and you get back clear metrics and visual feedback — cadence, vertical bounce, knee angle, and more. No wearables or lab required. I built it because I wanted a quick, honest read on my own gait without the jargon.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-white mb-3">How the analysis works</h2>
        <p className="text-gray-300 leading-relaxed">
          We use computer vision to track your joints frame by frame, then measure things like cadence, vertical bounce, and stride length against research-backed targets. The pipeline combines MediaPipe Pose for body tracking with rule-based heuristics tuned for running — so you get numbers and flags that are easy to act on.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-white mb-3">What Runlens is not</h2>
        <p className="text-gray-300 leading-relaxed">
          Runlens is a fitness tool, not a medical device. It can&apos;t diagnose injuries or replace a physio or running coach. Think of it as a second pair of eyes on your form — the kind you&apos;d get from a knowledgeable friend.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-white mb-4">Metrics explained</h2>
        <div className="overflow-x-auto rounded-lg border border-white/10">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-secondary border-b border-white/10">
                <th className="text-left p-3 text-gray-200 font-medium">Metric</th>
                <th className="text-left p-3 text-gray-200 font-medium">Target</th>
                <th className="text-left p-3 text-gray-200 font-medium">What it means</th>
              </tr>
            </thead>
            <tbody>
              {METRICS.map((row) => (
                <tr key={row.metric} className="border-b border-white/5">
                  <td className="p-3 text-gray-300">{row.metric}</td>
                  <td className="p-3 text-gray-300">{row.target}</td>
                  <td className="p-3 text-gray-400">{row.meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <button
          type="button"
          onClick={() => setTechOpen((o) => !o)}
          className="flex items-center gap-2 text-primary hover:underline font-medium"
        >
          {techOpen ? "▼" : "▶"} Tech stack
        </button>
        {techOpen && (
          <p className="mt-3 text-gray-400 text-sm">
            Runlens is built with Next.js, FastAPI, MediaPipe, and Cloudflare R2. It runs on Render and Vercel.
          </p>
        )}
      </section>

      <Footer />
    </div>
  );
}

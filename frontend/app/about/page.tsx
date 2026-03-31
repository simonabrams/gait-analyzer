"use client";

import { useState } from "react";
import Link from "next/link";
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
    <div>
      {/* Hero */}
      <section
        className="min-h-[50vh] flex flex-col justify-center py-24 relative overflow-hidden"
        style={{
          backgroundImage: "url(https://picsum.photos/seed/trail-runner/1600/900)",
          backgroundSize: "cover",
          backgroundPosition: "center 30%",
        }}
      >
        <div className="absolute inset-0 bg-black/60" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20" />
        <div className="relative z-10 max-w-3xl mx-auto px-6">
          <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-4">
            About Runlens
          </p>
          <h1 className="text-4xl md:text-6xl font-bold text-white leading-tight mb-6">
            Built by a runner,<br />for runners.
          </h1>
          <p className="text-lg text-gray-300 leading-relaxed max-w-xl">
            A simple tool that helps you see what&apos;s going on with your running form — no wearables or lab required.
          </p>
        </div>
      </section>

      {/* Intro */}
      <section className="py-20 bg-background">
        <div className="max-w-5xl mx-auto px-6 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-3">
              The Story
            </p>
            <h2 className="text-2xl font-bold text-white mb-4">What is Runlens?</h2>
            <p className="text-gray-300 leading-relaxed">
              Upload a short video from the side, and you get back clear metrics and visual
              feedback — cadence, vertical bounce, knee angle, and more. I built it because I
              wanted a quick, honest read on my own gait without the jargon.
            </p>
          </div>
          <div
            className="rounded-2xl overflow-hidden h-56 relative"
            style={{
              backgroundImage: "url(https://picsum.photos/seed/runner-side/800/500)",
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          >
            <div className="absolute inset-0 bg-gradient-to-tr from-black/60 via-transparent to-transparent" />
          </div>
        </div>
      </section>

      {/* How the analysis works */}
      <section
        className="py-20 relative overflow-hidden"
        style={{
          backgroundImage: "url(https://picsum.photos/seed/motion-capture/1600/800)",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0 bg-black/75" />
        <div className="relative z-10 max-w-3xl mx-auto px-6">
          <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-3">
            The Analysis
          </p>
          <h2 className="text-2xl font-bold text-white mb-4">How the analysis works</h2>
          <p className="text-gray-300 leading-relaxed">
            We use computer vision to track your joints frame by frame, then measure things like
            cadence, vertical bounce, and stride length against research-backed targets. The
            pipeline combines MediaPipe Pose for body tracking with rule-based heuristics tuned
            for running — so you get numbers and flags that are easy to act on.
          </p>
        </div>
      </section>

      {/* Metrics */}
      <section className="py-20 bg-background">
        <div className="max-w-3xl mx-auto px-6">
          <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-3">
            The Numbers
          </p>
          <h2 className="text-2xl font-bold text-white mb-8">Metrics explained</h2>
          <div className="rounded-2xl border border-white/10 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-white/5 border-b border-white/10">
                  <th className="text-left px-5 py-3 text-gray-300 font-medium">Metric</th>
                  <th className="text-left px-5 py-3 text-gray-300 font-medium">Target</th>
                  <th className="text-left px-5 py-3 text-gray-300 font-medium">What it means</th>
                </tr>
              </thead>
              <tbody>
                {METRICS.map((row, i) => (
                  <tr
                    key={row.metric}
                    className={`border-b border-white/5 ${i % 2 === 0 ? "" : "bg-white/[0.02]"}`}
                  >
                    <td className="px-5 py-3 text-white font-medium">{row.metric}</td>
                    <td className="px-5 py-3 text-primary font-mono">{row.target}</td>
                    <td className="px-5 py-3 text-gray-400">{row.meaning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Disclaimer + Tech */}
      <section className="py-20 bg-background border-t border-white/5">
        <div className="max-w-3xl mx-auto px-6 space-y-10">
          <div className="rounded-2xl border border-amber-400/20 bg-amber-400/5 p-6">
            <p className="text-xs font-semibold tracking-[0.2em] uppercase text-amber-400 mb-2">
              Important
            </p>
            <h3 className="text-lg font-semibold text-white mb-2">What Runlens is not</h3>
            <p className="text-gray-300 leading-relaxed text-sm">
              Runlens is a fitness tool, not a medical device. It can&apos;t diagnose injuries or
              replace a physio or running coach. Think of it as a second pair of eyes on your
              form — the kind you&apos;d get from a knowledgeable friend.
            </p>
          </div>

          <div>
            <button
              type="button"
              onClick={() => setTechOpen((o) => !o)}
              className="flex items-center gap-2 text-primary hover:opacity-80 font-medium transition-opacity"
            >
              <span className="text-xs">{techOpen ? "▼" : "▶"}</span> Tech stack
            </button>
            {techOpen && (
              <p className="mt-3 text-gray-400 text-sm leading-relaxed">
                Runlens is built with Next.js, FastAPI, MediaPipe, and Cloudflare R2. It runs on
                Render and Vercel.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section
        className="py-24 relative overflow-hidden"
        style={{
          backgroundImage: "url(https://picsum.photos/seed/running-track/1600/800)",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0 bg-black/70" />
        <div className="relative z-10 max-w-2xl mx-auto px-6 text-center">
          <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-4">
            Ready to start?
          </p>
          <h2 className="text-3xl font-bold text-white mb-6">See your form in action.</h2>
          <Link
            href="/#upload"
            className="inline-block bg-primary text-background font-semibold px-8 py-3.5 rounded-lg hover:opacity-90 transition-opacity"
          >
            Analyze a Run →
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}

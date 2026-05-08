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
          backgroundImage: "url(images/about-hero-bg.jpg)",
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
              feedback — cadence, vertical bounce, knee angle, and more. I built it because I wanted to learn how I could improve my form using a lens (get it?) outside of the numbers on my Apple Watch and iPhone.
            </p>
          </div>
          <div
            className="rounded-2xl overflow-hidden h-56 relative"
            style={{
              backgroundImage: "url(images/annotated-run.jpg)",
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
            Runlens uses computer vision to track your joints frame by frame, then measures things like
            cadence, vertical bounce, and stride length against research-backed targets. The
            pipeline combines MediaPipe Pose for body tracking with rule-based heuristics tuned
            for running — so you get numbers and flags that are easy to act on.
          </p>
          <p className="text-gray-300 leading-relaxed">
            Please be aware that results might vary from what you get on your wearables or fitness trackers; these devices use onboard accelerometers to analyze your motion; Runlens uses computer vision and the accuracy will be affected by things like motion blur, poor lighting and other environmental factors. As such, our results are best used as directional insights and trends, not clinical measurements.
          </p>
          <p className="text-gray-300 leading-relaxed">One final note: a running coach told me that if her runners don't have any issues with pain or injury while running, then she doesn't bother to correct their form. Human bodies are all different and they work the way they work, so if that's you, then you might not need Runlens. But, if you're curious about your form, and want some quick insights, then Runlens might be the tool you're looking for. Either way, happy running! 🏃</p>
        </div>
      </section>

      {/* Tips */}
      <section className="py-20 bg-secondary">
        <div className="max-w-3xl mx-auto px-6">
          <p className="text-primary text-xs font-semibold tracking-[0.2em] uppercase mb-3">
            Best Results
          </p>
          <h2 className="text-2xl font-bold text-white mb-2">Tips for accurate analysis</h2>
          <p className="text-gray-400 text-sm mb-10">
            Computer vision is sensitive to how the video is recorded. These tips make a big difference.
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {[
              {
                title: "Shoot from the side",
                body: "Place your camera at a strict 90° angle to your direction of travel. Even a slight diagonal angle throws off joint angle and stride calculations.",
              },
              {
                title: "Use 60 fps or higher",
                body: "Higher frame rates reduce motion blur and give the pose tracker more frames to work with. 30 fps is the minimum; 60 fps or 120 fps produces noticeably better results.",
              },
              {
                title: "Keep the camera level and still",
                body: "Mount it on a tripod or prop it against something stable. A shaky or panning camera makes landmark tracking unreliable.",
              },
              {
                title: "Frame your whole body",
                body: "Leave a little headroom above and show your feet clearly. Cropping out your head or feet causes the pose model to guess those joints, reducing accuracy.",
              },
              {
                title: "Film in good, even light",
                body: "Outdoor daylight is ideal. Avoid filming with the sun or a bright window directly behind you — backlighting washes out your silhouette and hurts detection.",
              },
              {
                title: "Wear fitted clothing",
                body: "Loose or baggy clothes obscure joint positions. Fitted running kit gives the pose model a much clearer view of your hips, knees, and ankles.",
              },
              {
                title: "Keep clips short",
                body: "10–30 seconds (covering several full stride cycles) is the sweet spot. Longer clips take more time to process and don't meaningfully improve the results.",
              },
              {
                title: "Simple backgrounds help",
                body: "A plain wall, road, or open field behind you makes it easier to isolate your body. Busy or high-contrast backgrounds (crowds, fences, foliage) can confuse the tracker.",
              },
            ].map((tip) => (
              <div
                key={tip.title}
                className="rounded-xl border border-white/10 bg-background p-5"
              >
                <p className="text-white font-semibold mb-1 text-sm">{tip.title}</p>
                <p className="text-gray-400 text-sm leading-relaxed">{tip.body}</p>
              </div>
            ))}
          </div>
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
          backgroundImage: "url(images/silhouette-run.jpg)",
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
          <p className="mt-6 text-gray-400 text-sm">
            Questions or feedback?{" "}
            <a href="mailto:hi@runlens.io" className="text-primary hover:underline">
              hi@runlens.io
            </a>
          </p>
        </div>
      </section>

      <Footer />
    </div>
  );
}

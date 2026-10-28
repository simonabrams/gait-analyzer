import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getRun } from "@/lib/api";
import MetricCards from "@/components/MetricCards";
import SummaryStrip from "@/components/SummaryStrip";
import WhatToWorkOn from "@/components/WhatToWorkOn";
import StrideCharts from "@/components/StrideCharts";
import ShareButton from "@/components/ShareButton";
import ExportMenu from "@/components/ExportMenu";
import ClaimBanner from "@/components/ClaimBanner";
import DeleteScanButton from "@/components/DeleteScanButton";
import AddRearVideoControl from "@/components/AddRearVideoControl";
import RearViewSection from "@/components/RearViewSection";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ justCreated?: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  let run;
  try {
    run = await getRun(id);
  } catch {
    return { title: "Run Report" };
  }
  const summary = run.results?.summary;
  const desc =
    summary &&
    [
      summary.cadence_avg != null && `Cadence: ${summary.cadence_avg} spm`,
      summary.vertical_osc_avg_cm != null &&
        `Bounce: ${summary.vertical_osc_avg_cm} cm`,
      summary.knee_angle_strike_avg_deg != null &&
        `Knee drive: ${summary.knee_angle_strike_avg_deg}°`,
    ]
      .filter(Boolean)
      .join(" · ");
  return {
    title: `Gait Analysis – Run ${id.slice(0, 8)}`,
    description: desc || "Running gait analysis results",
    openGraph: {
      title: `Gait Analysis – Run ${id.slice(0, 8)}`,
      description: desc || "Running gait analysis results",
    },
  };
}

function SectionEyebrow({ label }: { label: string }) {
  return (
    <p className="text-xs font-semibold tracking-widest text-primary uppercase">{label}</p>
  );
}

/** One bordered/black video box, matching the page's pre-existing single-video
 * styling exactly. `label` is only shown once there's a second video to tell
 * apart from (see the grid vs. single-video branch below) — with no rear
 * video, this renders pixel-identical to how the page looked before. */
function AnnotatedVideo({ src, label }: { src: string; label: string | null }) {
  return (
    <div className="relative bg-black rounded-xl overflow-hidden border border-white/10 flex justify-center">
      <video src={src} controls className="max-h-[520px] w-auto" preload="metadata">
        Your browser does not support the video tag.
      </video>
      <div className="absolute bottom-3 left-3 flex items-center gap-2 pointer-events-none">
        {label && (
          <span className="text-xs font-semibold tracking-widest text-white/70 uppercase bg-black/60 px-2 py-1 rounded">
            {label}
          </span>
        )}
        <span className="text-xs font-semibold tracking-widest text-primary uppercase bg-black/60 px-2 py-1 rounded">
          Skeleton Overlay
        </span>
      </div>
    </div>
  );
}

interface ConfidenceGate {
  hardFail: boolean;
  lowConfidence: boolean;
  usableStrideCount: number | null;
  userMessage: string | null;
}

/** Read backend/confidence_gate.py's info out of results.meta.confidence_gate
 * (an untyped Record from the API) — see job_runner.py for what sets this. */
function getConfidenceGate(meta: Record<string, unknown> | undefined): ConfidenceGate | null {
  const gate = meta?.confidence_gate;
  if (!gate || typeof gate !== "object") return null;
  const g = gate as Record<string, unknown>;
  return {
    hardFail: g.hard_fail === true,
    lowConfidence: g.low_confidence === true,
    usableStrideCount: typeof g.usable_stride_count === "number" ? g.usable_stride_count : null,
    userMessage: typeof g.user_message === "string" ? g.user_message : null,
  };
}

function formatDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

export default async function RunResultPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { justCreated } = await searchParams;
  let run;
  try {
    run = await getRun(id);
  } catch {
    notFound();
  }

  if (run.status === "processing") {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-4">
        <h1 className="text-2xl font-bold text-white">Analysis in progress</h1>
        <p className="text-gray-400">This run is still being processed. Refresh in a moment.</p>
        <Link href="/runs" className="text-primary hover:underline text-sm">
          Back to run history
        </Link>
      </div>
    );
  }

  if (run.status === "failed") {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-4">
        <h1 className="text-2xl font-bold text-white">Analysis failed</h1>
        <p className="text-red-400">{run.error_message ?? "Unknown error"}</p>
        <Link href="/runs" className="text-primary hover:underline text-sm">
          Back to run history
        </Link>
      </div>
    );
  }

  const summary = run.results?.summary;
  const flags = run.results?.flags;
  const analyzedDate = formatDate(run.created_at);
  const gate = getConfidenceGate(run.results?.meta);

  // A completed run with an empty summary means pose/stride detection produced
  // no usable data (wrong angle, walking, too short, etc.) — or the confidence
  // gate hard-failed it (too few usable strides, or an implausible aggregate
  // value like a halved cadence). Either way, same screen: see gate.userMessage
  // below for why, when we know a specific reason.
  const hasData = summary != null && Object.keys(summary).length > 0;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-10">

      <ClaimBanner show={justCreated === "1"} />

      {/* Page header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <SectionEyebrow label={hasData ? "Analysis Complete" : "Analysis Finished"} />
          <h1 className="text-3xl font-bold text-white">Your Run Report</h1>
          {analyzedDate && (
            <p className="text-sm text-gray-400">Analyzed {analyzedDate}</p>
          )}
        </div>
        <div className="flex items-center gap-2 pt-1">
          <ShareButton runId={id} />
          <ExportMenu runId={id} />
          <DeleteScanButton runId={id} />
        </div>
      </div>

      {/* Annotated video(s) — side-by-side once a rear video exists, otherwise
          the same single centered video as always (no visual change). */}
      {run.annotated_video_url && (
        <div
          className={
            run.rear_video_url ? "grid grid-cols-1 md:grid-cols-2 gap-4" : "flex justify-center"
          }
        >
          <AnnotatedVideo src={run.annotated_video_url} label={run.rear_video_url ? "Side View" : null} />
          {run.rear_video_url && <AnnotatedVideo src={run.rear_video_url} label="Rear View" />}
        </div>
      )}

      <AddRearVideoControl runId={id} />

      {hasData ? (
        <>
          {gate?.lowConfidence && (
            <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-5 py-3 text-sm text-amber-300">
              {gate.usableStrideCount != null
                ? `Based on ${gate.usableStrideCount} detected strides — lower confidence than usual.`
                : "Lower confidence than usual — fewer strides detected than ideal."}
            </div>
          )}

          <SummaryStrip summary={summary} flags={flags} rearView={run.results?.rear_view} />

          {/* Key metrics */}
          <div className="space-y-4">
            <div>
              <SectionEyebrow label="Key Metrics" />
              <h2 className="text-xl font-semibold text-white mt-1">Performance Overview</h2>
            </div>
            <MetricCards summary={summary} flags={flags} />
          </div>

          <p className="text-xs text-gray-500 leading-relaxed">
            Video-derived estimates — best for comparing your own sessions over time, not for
            clinical use.{" "}
            <Link href="/about" className="text-primary hover:underline">
              How we measure
            </Link>
          </p>

          {/* What to work on — side-view findings only (see WhatToWorkOn.tsx
              for why rear patterns don't get an equivalent card here). */}
          <div className="space-y-4">
            <div>
              <SectionEyebrow label="Focus Areas" />
              <h2 className="text-xl font-semibold text-white mt-1">What to Work On</h2>
            </div>
            <WhatToWorkOn flags={flags} strides={run.results?.strides as Array<Record<string, unknown>> | undefined} />
          </div>

          {/* No more pre-rendered dashboard.png here — StrideCharts below now
              covers the same four metrics natively. The backend still
              generates/uploads that PNG for the PDF export (pdf_report.py),
              which hasn't been moved to native charts yet — see the plan
              file for that as a separate follow-up. */}

          {/* Stride by stride — supporting detail, side-view only this pass. */}
          <div className="space-y-4">
            <div>
              <SectionEyebrow label="Supporting Detail" />
              <h2 className="text-xl font-semibold text-white mt-1">Stride by Stride</h2>
            </div>
            <StrideCharts strides={run.results?.strides as Array<Record<string, unknown>> | undefined} />
          </div>
        </>
      ) : (
        /* No data — explain why and what to try */
        <div className="bg-secondary border border-white/10 rounded-xl p-7 space-y-5">
          <div className="flex items-start gap-4">
            <span className="text-3xl leading-none mt-0.5">🤔</span>
            <div>
              <h2 className="text-xl font-semibold text-white">
                We couldn&apos;t measure your gait this time
              </h2>
              <p className="text-gray-400 text-sm mt-1.5 leading-relaxed">
                Our AI analyses your run by tracking the movement of your feet and legs
                frame by frame. This time, we weren&apos;t able to pick up a clear enough
                pattern to generate stats — but don&apos;t worry, it&apos;s usually just a
                filming angle thing.
              </p>
              {gate?.userMessage && (
                <p className="text-amber-300 text-sm mt-3 leading-relaxed">
                  {gate.userMessage}
                </p>
              )}
            </div>
          </div>

          <div className="border-t border-white/10 pt-5">
            <p className="text-xs font-semibold tracking-widest text-primary uppercase mb-3">
              Common reasons &amp; fixes
            </p>
            <ul className="space-y-3">
              {[
                {
                  icon: "📐",
                  title: "Film from the side",
                  detail:
                    "Your main video needs a side-on view — front or back angles can't show stride, knee drive or lean. Rear-view clips go in the separate rear-view slot.",
                },
                {
                  icon: "📏",
                  title: "Make sure your full body is visible",
                  detail:
                    "We need to see your head, hips, and feet throughout the clip. If your feet are cut off, the analysis won't work.",
                },
                {
                  icon: "🏃",
                  title: "Run, don't walk",
                  detail:
                    "The analyser is tuned for running. Walking or very slow jogging may not produce enough clear stride data.",
                },
                {
                  icon: "⏱️",
                  title: "Aim for 10–15 seconds of steady running",
                  detail:
                    "Treadmill or outdoors both work — just trim out the first/last couple steps where you're speeding up or slowing down.",
                },
                {
                  icon: "🤳",
                  title: "Keep the camera steady",
                  detail:
                    "A tripod or bracing your phone against something works best. If a friend is filming outdoors, have them stand still rather than jog alongside you — a shaky shot mostly throws off the bounce measurement.",
                },
              ].map(({ icon, title, detail }) => (
                <li key={title} className="flex items-start gap-3">
                  <span className="text-lg leading-none mt-0.5">{icon}</span>
                  <div>
                    <p className="text-sm font-medium text-white">{title}</p>
                    <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{detail}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="border-t border-white/10 pt-5">
            <Link
              href="/#upload"
              className="inline-block bg-primary text-background font-semibold text-sm px-5 py-2.5 rounded-lg hover:opacity-90 transition-opacity"
            >
              Try another video →
            </Link>
          </div>
        </div>
      )}

      {/* Rear-view patterns — independent of the side view's own hasData/gate:
          a rear scan can succeed even when the side one didn't, and vice versa. */}
      {run.results?.rear_view && !["processing", "failed"].includes(run.results.rear_view.status) && (
        <div className="space-y-4">
          <div>
            <SectionEyebrow label="Rear View" />
            <h2 className="text-xl font-semibold text-white mt-1">Balance &amp; Alignment</h2>
          </div>
          <RearViewSection rearView={run.results.rear_view} />
        </div>
      )}

    </div>
  );
}

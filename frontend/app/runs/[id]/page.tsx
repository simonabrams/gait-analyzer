import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getRun } from "@/lib/api";
import MetricCards from "@/components/MetricCards";
import FeedbackCards from "@/components/FeedbackCards";
import ShareButton from "@/components/ShareButton";
import PdfReportButton from "@/components/PdfReportButton";
import AccuracyBanner from "@/components/AccuracyBanner";
import ClaimBanner from "@/components/ClaimBanner";

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
    return { title: "Gait Analyzer" };
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

  // A completed run with an empty summary means pose/stride detection produced
  // no usable data (wrong angle, walking, too short, etc.)
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
          {hasData && <PdfReportButton runId={id} />}
          <Link
            href="/runs"
            className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors"
          >
            Run history
          </Link>
        </div>
      </div>

      {/* Annotated video */}
      {run.annotated_video_url && (
        <div className="relative bg-black rounded-xl overflow-hidden border border-white/10 flex justify-center">
          <video
            src={run.annotated_video_url}
            controls
            className="max-h-[520px] w-auto"
            preload="metadata"
          >
            Your browser does not support the video tag.
          </video>
          <div className="absolute bottom-3 left-3 flex items-center gap-2 pointer-events-none">
            <span className="text-xs font-semibold tracking-widest text-primary uppercase bg-black/60 px-2 py-1 rounded">
              Skeleton Overlay
            </span>
          </div>
        </div>
      )}

      {hasData ? (
        <>
          <AccuracyBanner />

          {/* Key metrics */}
          <div className="space-y-4">
            <div>
              <SectionEyebrow label="Key Metrics" />
              <h2 className="text-xl font-semibold text-white mt-1">Performance Overview</h2>
            </div>
            <MetricCards summary={summary} />
          </div>

          {/* Form breakdown / feedback */}
          <div className="space-y-4">
            <div>
              <SectionEyebrow label="AI Analysis" />
              <h2 className="text-xl font-semibold text-white mt-1">Form Breakdown</h2>
            </div>
            <FeedbackCards flags={flags} hasData={true} />
          </div>

          {/* Dashboard image */}
          {run.dashboard_image_url && (
            <div className="space-y-4">
              <div>
                <SectionEyebrow label="Stride Charts" />
                <h2 className="text-xl font-semibold text-white mt-1">Metrics Over Time</h2>
              </div>
              <div className="bg-secondary border border-white/10 rounded-xl overflow-hidden">
                <img
                  src={run.dashboard_image_url}
                  alt="Run dashboard"
                  className="w-full h-auto"
                />
              </div>
            </div>
          )}
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
                    "A direct side-on view is essential — front or back angles make it very hard to track stride patterns.",
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
                  title: "Give it at least 20–30 seconds",
                  detail:
                    "Shorter clips might not contain enough strides for a reliable analysis. A 30–60 second clip on a treadmill works best.",
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

    </div>
  );
}

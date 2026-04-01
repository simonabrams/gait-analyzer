import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getRun } from "@/lib/api";
import MetricCards from "@/components/MetricCards";
import FeedbackCards from "@/components/FeedbackCards";
import ShareButton from "@/components/ShareButton";

type Props = { params: Promise<{ id: string }> };

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
        `Vertical oscillation: ${summary.vertical_osc_avg_cm} cm`,
      summary.knee_angle_strike_avg_deg != null &&
        `Knee angle: ${summary.knee_angle_strike_avg_deg}°`,
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

export default async function RunResultPage({ params }: Props) {
  const { id } = await params;
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

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-10">

      {/* Page header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <SectionEyebrow label="Analysis Complete" />
          <h1 className="text-3xl font-bold text-white">Your Run Report</h1>
          {analyzedDate && (
            <p className="text-sm text-gray-400">Analyzed {analyzedDate}</p>
          )}
        </div>
        <div className="flex items-center gap-2 pt-1">
          <ShareButton />
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
        <div className="relative bg-black rounded-xl overflow-hidden border border-white/10">
          <video
            src={run.annotated_video_url}
            controls
            className="w-full"
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

      {/* Key metrics */}
      <div className="space-y-4">
        <div>
          <SectionEyebrow label="Key Metrics" />
          <h2 className="text-xl font-semibold text-white mt-1">Performance Overview</h2>
        </div>
        <MetricCards summary={summary} />
      </div>

      {/* Dashboard image */}
      {run.dashboard_image_url && (
        <div className="bg-secondary border border-white/10 rounded-xl overflow-hidden">
          <img
            src={run.dashboard_image_url}
            alt="Run dashboard"
            className="w-full h-auto"
          />
        </div>
      )}

      {/* Form breakdown / feedback */}
      <div className="space-y-4">
        <div>
          <SectionEyebrow label="AI Analysis" />
          <h2 className="text-xl font-semibold text-white mt-1">Form Breakdown</h2>
        </div>
        <FeedbackCards flags={flags} />
      </div>

    </div>
  );
}

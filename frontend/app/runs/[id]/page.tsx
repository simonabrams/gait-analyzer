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
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Analysis in progress</h1>
        <p className="text-gray-600">This run is still being processed. Refresh in a moment.</p>
        <Link href="/runs" className="text-blue-600 hover:underline">
          Back to run history
        </Link>
      </div>
    );
  }

  if (run.status === "failed") {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Analysis failed</h1>
        <p className="text-red-600">{run.error_message ?? "Unknown error"}</p>
        <Link href="/runs" className="text-blue-600 hover:underline">
          Back to run history
        </Link>
      </div>
    );
  }

  const summary = run.results?.summary;
  const flags = run.results?.flags;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-white">Run result</h1>
        <div className="flex items-center gap-2">
          <ShareButton />
          <Link href="/runs" className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors">
            Run history
          </Link>
        </div>
      </div>

      {run.annotated_video_url && (
        <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
          <video
            src={run.annotated_video_url}
            controls
            className="w-full"
            preload="metadata"
          >
            Your browser does not support the video tag.
          </video>
        </div>
      )}

      <MetricCards summary={summary} />

      {run.dashboard_image_url && (
        <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
          <img
            src={run.dashboard_image_url}
            alt="Dashboard"
            className="w-full h-auto"
          />
        </div>
      )}

      <FeedbackCards flags={flags} />
    </div>
  );
}

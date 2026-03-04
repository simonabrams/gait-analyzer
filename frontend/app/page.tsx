"use client";

import { useRouter } from "next/navigation";
import VideoUploader from "@/components/VideoUploader";

export default function HomePage() {
  const router = useRouter();

  const handleComplete = (runId: string) => {
    router.push(`/runs/${runId}`);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Upload a run video</h1>
      <p className="text-gray-600">
        Film from the side, full body visible. MP4 or MOV, up to 500 MB.
      </p>
      <VideoUploader onComplete={handleComplete} />
    </div>
  );
}

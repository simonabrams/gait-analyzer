"use client";

import { useCallback, useEffect, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { getRunStatus } from "@/lib/api";
import { getStoredAnonId } from "@/lib/anon";
import { ALLOWED_VIDEO_TYPES, MAX_VIDEO_SIZE_BYTES, rejectionMessage } from "@/lib/videoValidation";
import { useRearVideoUpload } from "@/lib/useRearVideoUpload";
import ConsentModal from "@/components/ConsentModal";
import FileRejectionAlert from "@/components/FileRejectionAlert";
import UpgradeModal from "@/components/UpgradeModal";

/** Lets the OWNER of a completed run attach an optional rear-view video after
 * the fact (POST /api/runs/{id}/rear-video — independent of the side
 * analysis, never blocks or re-triggers it). Renders nothing for anyone else:
 * this page is a public share link (see middleware.ts), so ownership has to
 * be resolved server-side (RunStatusResponse.is_owner) rather than assumed
 * from being signed in at all, the way DeleteScanButton's purely-local
 * hasAnonRun() check can for its anonymous-only case. */
export default function AddRearVideoControl({ runId }: { runId: string }) {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [isOwner, setIsOwner] = useState(false);
  const [initialRearStatus, setInitialRearStatus] = useState<string | null>(null);
  const [fileRejection, setFileRejection] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    let cancelled = false;
    (async () => {
      const token = isSignedIn ? (await getToken()) ?? undefined : undefined;
      const anonId = token ? undefined : getStoredAnonId() ?? undefined;
      try {
        const s = await getRunStatus(runId, token, anonId);
        if (cancelled) return;
        setIsOwner(s.is_owner);
        setInitialRearStatus(s.rear_status);
      } catch {
        // Ownership couldn't be confirmed — fail closed (stays hidden).
      } finally {
        if (!cancelled) setChecked(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, runId, getToken]);

  const upload = useRearVideoUpload(runId, {
    initialStatus: initialRearStatus,
    onComplete: () => router.refresh(),
  });

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      setFileRejection(rejectionMessage(rejected));
      if (accepted[0]) upload.submit(accepted[0]);
    },
    [upload],
  );

  const busy = upload.status === "uploading" || upload.status === "processing";
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ALLOWED_VIDEO_TYPES,
    maxSize: MAX_VIDEO_SIZE_BYTES,
    maxFiles: 1,
    multiple: false,
    disabled: busy,
  });

  if (!checked || !isOwner || upload.status === "complete") return null;

  return (
    <div className="bg-secondary border border-white/10 rounded-xl p-5 space-y-3">
      <div className="flex items-center gap-2">
        <p className="text-sm font-medium text-white">Add a rear-view video</p>
        <span className="text-[10px] font-semibold tracking-wide text-gray-400 uppercase bg-white/10 px-1.5 py-0.5 rounded">
          Optional
        </span>
      </div>
      <p className="text-xs text-gray-400 leading-relaxed">
        A clip filmed from directly behind shows hip drop, knee alignment and step width,
        patterns a side-on video can&apos;t see. It&apos;s analysed separately and never
        changes the results above.
      </p>

      {busy ? (
        <div className="space-y-2">
          <div className="h-2 bg-white/10 rounded overflow-hidden">
            {upload.status === "uploading" && upload.uploadProgress !== null ? (
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${upload.uploadProgress}%` }}
              />
            ) : (
              <div className="h-full w-1/3 bg-primary rounded animate-pulse" />
            )}
          </div>
          <p className="text-xs text-gray-400">
            {upload.status === "uploading"
              ? `Uploading… ${upload.uploadProgress ?? 0}%`
              : "Analysing rear-view video…"}
          </p>
        </div>
      ) : (
        <>
          {(upload.status === "failed" || initialRearStatus === "failed") && (
            <p className="text-amber-300 text-xs">
              {upload.error || "The previous attempt didn't finish — try again."}
            </p>
          )}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg px-4 py-5 text-center cursor-pointer transition-colors ${
              isDragActive
                ? "border-primary bg-primary/10"
                : fileRejection
                  ? "border-red-400/60 bg-red-400/5 hover:bg-red-400/10"
                  : "border-white/20 bg-white/5 hover:border-white/40 hover:bg-white/10"
            }`}
          >
            <input {...getInputProps()} />
            <p className="text-gray-300 text-xs font-medium">
              {isDragActive ? "Drop the video here" : "Drag and drop, or click to choose a video"}
            </p>
            <p className="text-gray-500 text-[11px] mt-1">MP4 or MOV · up to 100 MB</p>
          </div>
          <FileRejectionAlert message={fileRejection} />
        </>
      )}

      {upload.upgradeCode && (
        <UpgradeModal code={upload.upgradeCode} source="rear_video_upload" onClose={upload.dismissUpgrade} />
      )}
      {upload.showConsent && (
        <ConsentModal
          onAgree={upload.agreeConsent}
          onClose={upload.dismissConsent}
          busy={upload.consentBusy}
          error={upload.consentError}
        />
      )}
    </div>
  );
}

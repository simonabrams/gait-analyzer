"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useAuth, SignInButton } from "@clerk/nextjs";
import { createRunWithProgress, getRunStatus } from "@/lib/api";

const ALLOWED = { "video/mp4": [".mp4"], "video/quicktime": [".mov"] };
const MAX_SIZE = 500 * 1024 * 1024;

export default function VideoUploader({
  onComplete,
}: {
  onComplete: (runId: string) => void;
}) {
  const [height, setHeight] = useState(() => {
    if (typeof window === "undefined") return 175;
    const saved = localStorage.getItem("gait_height_cm");
    const parsed = saved ? Number(saved) : NaN;
    return isFinite(parsed) && parsed >= 100 && parsed <= 250 ? parsed : 175;
  });
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [processingProgress, setProcessingProgress] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [preprocessingWarning, setPreprocessingWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { isSignedIn, getToken } = useAuth();

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  const onDrop = useCallback((accepted: File[]) => {
    setFile(accepted[0] ?? null);
    setError(null);
  }, []);

  const isActive = uploadProgress !== null || processingProgress !== null;

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ALLOWED,
    maxSize: MAX_SIZE,
    maxFiles: 1,
    disabled: isActive,
  });

  const submit = async () => {
    if (!file) return;
    setError(null);
    setPreprocessingWarning(null);
    setUploadProgress(0);
    setProcessingProgress(null);
    setStatus("Uploading...");
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");

      const form = new FormData();
      form.append("file", file);
      form.append("height_cm", String(height));
      const { run_id } = await createRunWithProgress(form, token, (pct) => {
        setUploadProgress(pct);
      });

      // Upload done — switch to processing phase
      setUploadProgress(null);
      setProcessingProgress(0);
      setStatus("Processing...");

      // Exponential backoff: 2s → 4s → 8s (capped). Reduces poll requests from ~20 to ~8 per run.
      const poll = async (delay: number) => {
        const s = await getRunStatus(run_id);
        setProcessingProgress(s.progress);
        setStatus(s.status === "processing" ? "Processing..." : s.status);
        if (s.preprocessing_warning) setPreprocessingWarning(s.preprocessing_warning);
        if (s.status === "complete") {
          onComplete(run_id);
        } else if (s.status === "failed") {
          setError("Analysis failed.");
          setProcessingProgress(null);
        } else {
          // Still processing — schedule next poll with backed-off delay (max 8s)
          pollTimeoutRef.current = setTimeout(() => poll(Math.min(delay * 2, 8000)), delay);
        }
      };
      pollTimeoutRef.current = setTimeout(() => poll(2000), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setUploadProgress(null);
      setProcessingProgress(null);
      setStatus(null);
    }
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragActive
            ? "border-primary bg-primary/10"
            : "border-white/30 bg-white/5 hover:border-white/50 hover:bg-white/10"
        }`}
      >
        <input {...getInputProps()} />
        <p className="text-2xl mb-2">⬆️</p>
        {file ? (
          <p className="text-white text-sm">{file.name}</p>
        ) : (
          <>
            <p className="text-gray-200 font-medium text-sm">
              {isDragActive ? "Drop the video here" : "Drag and drop a video"}
            </p>
            <p className="text-gray-400 text-xs mt-1">MP4 or MOV · up to 500 MB</p>
          </>
        )}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-200 mb-1">Height (cm)</label>
        <input
          type="number"
          min={100}
          max={250}
          value={height}
          onChange={(e) => {
            const val = Number(e.target.value);
            setHeight(val);
            localStorage.setItem("gait_height_cm", String(val));
          }}
          className="border border-white/20 rounded-lg px-3 py-2 w-24 bg-white/10 text-white"
        />
      </div>
      {preprocessingWarning && (
        <div className="rounded-lg border border-amber-400/50 bg-amber-400/10 px-4 py-3 text-amber-300 text-sm">
          Your video was trimmed to 3 minutes for processing. For best results, upload a 30–60 second clip.
        </div>
      )}
      {uploadProgress !== null && (
        <div>
          <div className="h-2 bg-white/10 rounded overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-sm text-gray-300 mt-1">Uploading… {uploadProgress}%</p>
        </div>
      )}
      {processingProgress !== null && (
        <div>
          <div className="h-2 bg-white/10 rounded overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${processingProgress}%` }}
            />
          </div>
          <p className="text-sm text-gray-300 mt-1">{status} {processingProgress}%</p>
        </div>
      )}
      {error && <p className="text-red-400 text-sm">{error}</p>}
      {isSignedIn ? (
        <button
          type="button"
          onClick={submit}
          disabled={!file || isActive}
          className="w-full py-3 bg-primary text-background font-semibold rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          Analyze
        </button>
      ) : (
        <SignInButton mode="modal">
          <button
            type="button"
            className="w-full py-3 bg-primary text-background font-semibold rounded-lg hover:opacity-90 transition-opacity"
          >
            Sign in to Analyze
          </button>
        </SignInButton>
      )}
    </div>
  );
}

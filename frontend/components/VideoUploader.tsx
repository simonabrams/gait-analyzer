"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { createRun, getRunStatus } from "@/lib/api";

const ALLOWED = { "video/mp4": [".mp4"], "video/quicktime": [".mov"] };
const MAX_SIZE = 500 * 1024 * 1024;

export default function VideoUploader({
  onComplete,
}: {
  onComplete: (runId: string) => void;
}) {
  const [height, setHeight] = useState(175);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [preprocessingWarning, setPreprocessingWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const onDrop = useCallback((accepted: File[]) => {
    setFile(accepted[0] ?? null);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ALLOWED,
    maxSize: MAX_SIZE,
    maxFiles: 1,
    disabled: progress !== null,
  });

  const submit = async () => {
    if (!file) return;
    setError(null);
    setPreprocessingWarning(null);
    setProgress(0);
    setStatus("Uploading...");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("height_cm", String(height));
      const { run_id } = await createRun(form);
      setStatus("Processing...");
      pollRef.current = setInterval(async () => {
        const s = await getRunStatus(run_id);
        setProgress(s.progress);
        setStatus(s.status === "processing" ? "Processing..." : s.status);
        if (s.preprocessing_warning) setPreprocessingWarning(s.preprocessing_warning);
        if (s.status === "complete") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          onComplete(run_id);
        } else if (s.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setError("Analysis failed.");
          setProgress(null);
        }
      }, 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setProgress(null);
      setStatus(null);
    }
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white hover:border-gray-400"
        }`}
      >
        <input {...getInputProps()} />
        {file ? (
          <p className="text-gray-700">{file.name}</p>
        ) : (
          <p className="text-gray-600">
            {isDragActive ? "Drop the video here" : "Drag and drop a video (MP4/MOV), or click to select"}
          </p>
        )}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Height (cm)</label>
        <input
          type="number"
          min={100}
          max={250}
          value={height}
          onChange={(e) => setHeight(Number(e.target.value))}
          className="border rounded px-3 py-2 w-24"
        />
      </div>
      {preprocessingWarning && (
        <div className="rounded-lg border border-amber-400 bg-amber-50 px-4 py-3 text-amber-800 text-sm">
          Your video was trimmed to 3 minutes for processing. For best results, upload a 30–60 second clip.
        </div>
      )}
      {progress !== null && (
        <div>
          <div className="h-2 bg-gray-200 rounded overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-600 mt-1">{status} {progress}%</p>
        </div>
      )}
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <button
        type="button"
        onClick={submit}
        disabled={!file || progress !== null}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Analyze
      </button>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useAuth } from "@clerk/nextjs";
import {
  ApiError,
  createRunWithProgress,
  getConsentStatus,
  getRunStatus,
  recordConsent,
} from "@/lib/api";
import { getOrCreateAnonId, rememberAnonRun } from "@/lib/anon";
import {
  cmToFeetInches,
  feetInchesToCm,
  isHeightInRange,
  type HeightUnit,
} from "@/lib/height";
import ConsentModal from "@/components/ConsentModal";
import UpgradeModal from "@/components/UpgradeModal";
import posthog from "posthog-js";

function getProcessingStage(pct: number): string {
  if (pct >= 90) return "Writing report…";
  if (pct >= 70) return "Building dashboard…";
  if (pct >= 50) return "Generating annotated video…";
  if (pct >= 40) return "Computing metrics…";
  if (pct >= 10) return "Extracting pose data…";
  return "Preprocessing video…";
}

const ALLOWED = { "video/mp4": [".mp4"], "video/quicktime": [".mov"] };
// Sized for the 10-15s clip we now recommend (see HomeClient/about-page copy),
// not the old 30-60s guidance — generous headroom over what that actually
// produces, not a hard technical ceiling.
const MAX_SIZE = 100 * 1024 * 1024;

export default function VideoUploader({
  onComplete,
}: {
  onComplete: (runId: string) => void;
}) {
  // 0 means "not entered yet" (see heightError below) — we never default to
  // a placeholder height like 175: a wrong assumed height throws off every
  // real-world distance the analysis derives from it (stride length, bounce).
  // A previously-entered value is still remembered across visits — that's a
  // real confirmed height, not a guess.
  const [heightCm, setHeightCm] = useState(() => {
    if (typeof window === "undefined") return 0;
    const saved = localStorage.getItem("gait_height_cm");
    const parsed = saved ? Number(saved) : NaN;
    return isFinite(parsed) && parsed >= 100 && parsed <= 250 ? parsed : 0;
  });
  const [heightUnit, setHeightUnit] = useState<HeightUnit>(() => {
    if (typeof window === "undefined") return "cm";
    return localStorage.getItem("gait_height_unit") === "ftin" ? "ftin" : "cm";
  });
  const [feetInches, setFeetInches] = useState(() => cmToFeetInches(heightCm));
  const heightError =
    heightCm === 0
      ? "Enter your height — we use it to calibrate stride length and bounce to real-world units."
      : isHeightInRange(heightCm)
        ? null
        : `Height must be between 100–250 cm (about 3'3″–8'2″).`;
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [processingProgress, setProcessingProgress] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [preprocessingWarning, setPreprocessingWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [upgradeCode, setUpgradeCode] = useState<string | null>(null);
  const [consentOk, setConsentOk] = useState(false);
  const [showConsent, setShowConsent] = useState(false);
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [policyVersion, setPolicyVersion] = useState<string | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { isSignedIn, getToken } = useAuth();

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  const selectHeightUnit = (unit: HeightUnit) => {
    setHeightUnit(unit);
    localStorage.setItem("gait_height_unit", unit);
    if (unit === "ftin") setFeetInches(cmToFeetInches(heightCm));
  };

  const updateFeetInches = (feet: number, inches: number) => {
    let f = Math.max(0, Math.round(feet) || 0);
    let i = Math.max(0, Math.round(inches) || 0);
    if (i >= 12) {
      f += Math.floor(i / 12);
      i = i % 12;
    }
    setFeetInches({ feet: f, inches: i });
    const cm = feetInchesToCm(f, i);
    setHeightCm(cm);
    localStorage.setItem("gait_height_cm", String(cm));
  };

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
    multiple: false,
    disabled: isActive,
  });

  // Consent gate: the first Analyze click checks the server once; after that the
  // result is cached in state for the session. The backend enforces this too
  // (403 consent_required), so this is UX, not the security boundary.
  const submit = async () => {
    if (!file) return;
    setError(null);
    if (!consentOk) {
      try {
        const token = isSignedIn ? await getToken() : null;
        const anonId = token ? undefined : getOrCreateAnonId();
        const consentStatus = await getConsentStatus(token ?? undefined, anonId);
        setPolicyVersion(consentStatus.policy_version);
        if (!consentStatus.consented) {
          setConsentError(null);
          setShowConsent(true);
          return;
        }
        setConsentOk(true);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Couldn't check consent status");
        return;
      }
    }
    await startUpload();
  };

  const agreeConsent = async (ageConfirmed: boolean) => {
    setConsentBusy(true);
    setConsentError(null);
    try {
      const token = isSignedIn ? await getToken() : null;
      const anonId = token ? undefined : getOrCreateAnonId();
      const version =
        policyVersion ?? (await getConsentStatus(token ?? undefined, anonId)).policy_version;
      await recordConsent(version, token ?? undefined, anonId, ageConfirmed);
      setConsentOk(true);
      setShowConsent(false);
      await startUpload();
    } catch (e) {
      setConsentError(
        e instanceof Error ? e.message : "Couldn't save your consent — please try again.",
      );
    } finally {
      setConsentBusy(false);
    }
  };

  const startUpload = async () => {
    if (!file) return;
    setError(null);
    setUpgradeCode(null);
    setPreprocessingWarning(null);
    setUploadProgress(0);
    setProcessingProgress(null);
    setStatus("Uploading...");
    posthog.capture("analysis_submitted", {
      file_format: file.name.split(".").pop()?.toLowerCase() ?? "unknown",
      file_size_mb: Math.round((file.size / 1024 / 1024) * 10) / 10,
    });
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("height_cm", String(heightCm));
      const referralCode = localStorage.getItem("gait_referral_code");
      if (referralCode) form.append("referral_code", referralCode);

      // Use a longer-lived JWT template (10 min) so the token doesn't expire
      // mid-upload for large files on slow connections. The default session
      // token is only 60s, which isn't enough for multi-minute uploads.
      const token = isSignedIn ? await getToken({ template: "upload" }) : null;
      const anonId = token ? undefined : getOrCreateAnonId();

      const { run_id } = await createRunWithProgress(form, token ?? undefined, anonId, (pct) => {
        setUploadProgress(pct);
      });
      // Remember this run as "ours" so the anonymous visitor gets a self-serve
      // delete control on its results page (see lib/anon.ts, DeleteScanButton).
      if (anonId) rememberAnonRun(run_id);

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
      const errorMessage = e instanceof Error ? e.message : "Upload failed";
      setUploadProgress(null);
      setProcessingProgress(null);
      setStatus(null);
      if (e instanceof ApiError && e.code === "consent_required") {
        // Server-side gate caught a consent gap the client check missed
        // (e.g. the policy version was bumped mid-session) — re-prompt.
        setConsentOk(false);
        setConsentError(null);
        setShowConsent(true);
      } else if (e instanceof ApiError && e.code) {
        setUpgradeCode(e.code);
      } else {
        setError(errorMessage);
      }
      posthog.capture("upload_failed", {
        error_message_length: errorMessage.length,
        error_code: e instanceof ApiError ? e.code : undefined,
      });
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
            <p className="text-gray-400 text-xs mt-1">MP4 or MOV · up to 100 MB</p>
          </>
        )}
      </div>
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-sm font-medium text-gray-200">Height</label>
          <div className="inline-flex rounded-lg overflow-hidden border border-white/20 text-xs">
            {(["cm", "ftin"] as const).map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => selectHeightUnit(u)}
                className={`px-2.5 py-1 transition-colors ${
                  heightUnit === u
                    ? "bg-primary text-background font-semibold"
                    : "bg-white/10 text-gray-300 hover:bg-white/20"
                }`}
              >
                {u === "cm" ? "cm" : "ft/in"}
              </button>
            ))}
          </div>
        </div>
        {heightUnit === "cm" ? (
          <input
            type="number"
            min={100}
            max={250}
            placeholder="e.g. 175"
            value={heightCm === 0 ? "" : heightCm}
            onChange={(e) => {
              const val = Number(e.target.value);
              setHeightCm(val);
              localStorage.setItem("gait_height_cm", String(val));
            }}
            className={`border rounded-lg px-3 py-2 w-24 bg-white/10 text-white placeholder:text-gray-500 ${
              heightError ? "border-red-400/60" : "border-white/20"
            }`}
          />
        ) : (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={3}
                max={8}
                value={feetInches.feet}
                onChange={(e) => updateFeetInches(Number(e.target.value), feetInches.inches)}
                className={`border rounded-lg px-3 py-2 w-16 bg-white/10 text-white ${
                  heightError ? "border-red-400/60" : "border-white/20"
                }`}
              />
              <span className="text-gray-400 text-sm">ft</span>
            </div>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={0}
                max={11}
                value={feetInches.inches}
                onChange={(e) => updateFeetInches(feetInches.feet, Number(e.target.value))}
                className={`border rounded-lg px-3 py-2 w-16 bg-white/10 text-white ${
                  heightError ? "border-red-400/60" : "border-white/20"
                }`}
              />
              <span className="text-gray-400 text-sm">in</span>
            </div>
          </div>
        )}
        {heightError && <p className="text-red-400 text-xs mt-1">{heightError}</p>}
      </div>
      {preprocessingWarning && (
        <div className="rounded-lg border border-amber-400/50 bg-amber-400/10 px-4 py-3 text-amber-300 text-sm">
          Your video was trimmed to 3 minutes for processing. For best results, upload a 10–15 second clip of steady running.
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
        <div className="space-y-2">
          <div className="h-2 bg-white/10 rounded overflow-hidden">
            {processingProgress === 0 ? (
              <div className="h-full w-1/3 bg-primary rounded animate-pulse" />
            ) : (
              <div
                className="h-full bg-primary transition-all duration-500"
                style={{ width: `${processingProgress}%` }}
              />
            )}
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-300">{getProcessingStage(processingProgress)}</p>
            {processingProgress > 0 && (
              <p className="text-xs text-gray-500">{processingProgress}%</p>
            )}
          </div>
          {processingProgress === 0 && (
            <p className="text-xs text-gray-500">
              Larger videos take longer to preprocess — this can take a minute or two.
            </p>
          )}
        </div>
      )}
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <button
        type="button"
        onClick={submit}
        disabled={!file || isActive || !!heightError}
        className="w-full py-3 bg-primary text-background font-semibold rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
      >
        Analyze
      </button>
      {upgradeCode && (
        <UpgradeModal code={upgradeCode} source="upload_blocked" onClose={() => setUpgradeCode(null)} />
      )}
      {showConsent && (
        <ConsentModal
          onAgree={agreeConsent}
          onClose={() => setShowConsent(false)}
          busy={consentBusy}
          error={consentError}
        />
      )}
    </div>
  );
}

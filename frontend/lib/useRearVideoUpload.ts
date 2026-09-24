"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  ApiError,
  addRearVideoWithProgress,
  getConsentStatus,
  getRunStatus,
  recordConsent,
} from "@/lib/api";
import { getStoredAnonId } from "@/lib/anon";

export type RearUploadStatus = "idle" | "uploading" | "processing" | "complete" | "failed";

interface UseRearVideoUploadOptions {
  /** Seed state from a rear_status already known (e.g. from the same
   * getRunStatus call that decided whether to render the control at all). */
  initialStatus?: string | null;
  onComplete?: () => void;
}

/**
 * Upload/progress/poll mechanics for the optional rear-view video, factored
 * out of the results-page control (AddRearVideoControl) so PR 3 can reuse it
 * verbatim on the initial upload flow. Mirrors VideoUploader's submit /
 * agreeConsent / startUpload / poll structure closely — same consent gate,
 * same exponential-backoff polling, same ApiError-code branching — just
 * against POST /api/runs/{id}/rear-video instead of POST /api/runs.
 */
export function useRearVideoUpload(runId: string, options: UseRearVideoUploadOptions = {}) {
  const { initialStatus, onComplete } = options;
  const { isSignedIn, getToken } = useAuth();

  // NOT seeded from initialStatus in a lazy useState initializer: the caller
  // (AddRearVideoControl) doesn't know the real initialStatus until an async
  // ownership check resolves, one or more renders after this hook first
  // mounts — a lazy initializer would only ever see the pre-check value and
  // miss it. See the seeding effect below instead.
  const [status, setStatus] = useState<RearUploadStatus>("idle");
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [upgradeCode, setUpgradeCode] = useState<string | null>(null);
  const [showConsent, setShowConsent] = useState(false);
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [policyVersion, setPolicyVersion] = useState<string | null>(null);

  const pendingFileRef = useRef<File | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Ref, not a direct dependency: avoids re-subscribing the poll loop's
  // setTimeout chain if the caller passes a fresh onComplete on every render.
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  // Identity for THIS run's existing owner — never getOrCreateAnonId(), which
  // would mint a fresh id that doesn't match the run's owner and 404 the
  // upload. By the time any of this is reachable, is_owner has already been
  // confirmed true via one of these two credentials (see AddRearVideoControl).
  const ownerCredential = useCallback(async (): Promise<{ token?: string; anonId?: string }> => {
    const token = isSignedIn ? await getToken() : null;
    return token ? { token } : { anonId: getStoredAnonId() ?? undefined };
  }, [isSignedIn, getToken]);

  const pollUntilDone = useCallback(() => {
    const poll = async (delay: number) => {
      try {
        const s = await getRunStatus(runId);
        if (s.rear_status === "complete") {
          setStatus("complete");
          onCompleteRef.current?.();
          return;
        }
        if (s.rear_status === "failed") {
          setStatus("failed");
          return;
        }
      } catch {
        // Transient poll failure — keep trying rather than surface an error
        // mid-poll; the upload itself already succeeded at this point.
      }
      pollTimeoutRef.current = setTimeout(() => poll(Math.min(delay * 2, 8000)), delay);
    };
    pollTimeoutRef.current = setTimeout(() => poll(2000), 2000);
  }, [runId]);

  // Seeds status from initialStatus the first (and only the first) time it
  // resolves to a real value — covers both "already processing" (start
  // polling immediately, so a page refresh keeps showing live progress
  // instead of a static label) and "already complete/failed" from a
  // previous session. Runs once: later transitions come from startUpload/
  // pollUntilDone themselves, not from this prop.
  const seededRef = useRef(false);
  useEffect(() => {
    if (seededRef.current) return;
    if (initialStatus !== "processing" && initialStatus !== "failed" && initialStatus !== "complete") return;
    seededRef.current = true;
    setStatus(initialStatus);
    if (initialStatus === "processing") pollUntilDone();
  }, [initialStatus, pollUntilDone]);

  const startUpload = useCallback(
    async (file: File) => {
      setStatus("uploading");
      setError(null);
      setUpgradeCode(null);
      setUploadProgress(0);
      try {
        const form = new FormData();
        form.append("file", file);
        // Longer-lived template (10 min), same reasoning as the side upload —
        // the default 60s session token can expire mid-upload on a large file.
        const token = isSignedIn ? await getToken({ template: "upload" }) : null;
        const anonId = token ? undefined : getStoredAnonId() ?? undefined;
        await addRearVideoWithProgress(runId, form, token ?? undefined, anonId, (pct) => {
          setUploadProgress(pct);
        });
        setUploadProgress(null);
        setStatus("processing");
        pollUntilDone();
      } catch (e) {
        setUploadProgress(null);
        if (e instanceof ApiError && e.code === "consent_required") {
          // The run may predate a PRIVACY_POLICY_VERSION bump — a real,
          // expected case here, not just copy-paste from VideoUploader.
          setStatus("idle");
          pendingFileRef.current = file;
          setConsentError(null);
          setShowConsent(true);
        } else if (e instanceof ApiError && e.code) {
          setStatus("idle");
          setUpgradeCode(e.code);
        } else {
          setStatus("failed");
          setError(e instanceof Error ? e.message : "Upload failed");
        }
      }
    },
    [runId, isSignedIn, getToken, pollUntilDone],
  );

  // Consent gate: checked once up front, same as VideoUploader.submit — the
  // backend enforces this too (403 consent_required, handled in startUpload
  // above), so this is UX, not the security boundary.
  const submit = useCallback(
    async (file: File) => {
      pendingFileRef.current = file;
      setError(null);
      try {
        const { token, anonId } = await ownerCredential();
        const consentStatus = await getConsentStatus(token, anonId);
        setPolicyVersion(consentStatus.policy_version);
        if (!consentStatus.consented) {
          setConsentError(null);
          setShowConsent(true);
          return;
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Couldn't check consent status");
        return;
      }
      await startUpload(file);
    },
    [ownerCredential, startUpload],
  );

  const agreeConsent = useCallback(
    async (ageConfirmed: boolean) => {
      setConsentBusy(true);
      setConsentError(null);
      try {
        const { token, anonId } = await ownerCredential();
        const version = policyVersion ?? (await getConsentStatus(token, anonId)).policy_version;
        await recordConsent(version, token, anonId, ageConfirmed);
        setShowConsent(false);
        const file = pendingFileRef.current;
        if (file) await startUpload(file);
      } catch (e) {
        setConsentError(e instanceof Error ? e.message : "Couldn't save your consent — please try again.");
      } finally {
        setConsentBusy(false);
      }
    },
    [ownerCredential, policyVersion, startUpload],
  );

  const dismissConsent = useCallback(() => {
    setShowConsent(false);
    pendingFileRef.current = null;
  }, []);

  const dismissUpgrade = useCallback(() => setUpgradeCode(null), []);

  return {
    status,
    uploadProgress,
    error,
    upgradeCode,
    dismissUpgrade,
    showConsent,
    consentBusy,
    consentError,
    submit,
    agreeConsent,
    dismissConsent,
  };
}

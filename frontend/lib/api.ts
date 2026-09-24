// Video uploads go from the browser directly to the Render backend (createRun uses
// API_BASE below). They never go through a Next.js API route, so Vercel's 4.5MB
// payload limit does not apply. Keep uploads pointing at the backend URL only.

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");
if (!API_BASE) {
  throw new Error("NEXT_PUBLIC_API_URL is not set. Set it in .env.local (dev) or Vercel env (production).");
}

/** Replace with a real sample run ID when you have an analysis to showcase. */
export const SAMPLE_RUN_ID = "377504bc-4de2-4322-889d-8c14819991c9";

export interface RunCreated {
  run_id: string;
  status: string;
}

export interface RunStatus {
  status: string;
  progress: number;
  preprocessing_warning: string | null;
  // State of the optional rear-view video: null (none added), "processing",
  // "complete" or "failed" — independent of `status` above.
  rear_status: string | null;
  // True only when the caller's credentials (token or anon id, whichever was
  // sent) match this run's owner. Always false with no credentials at all —
  // this endpoint stays public/pollable by anyone with the link.
  is_owner: boolean;
}

export interface RearVideoCreated {
  run_id: string;
  rear_status: string;
}

export interface FlagExercise {
  name: string;
  description: string;
}

/** One entry from results.flags (backend/heuristics.py). Most flags carry
 * `severity` and `exercises`; the special `cadence_confidence` flag (a
 * measurement-reliability warning, not a performance finding) carries
 * neither — callers building a severity-sorted "what to work on" list should
 * filter to flags that have `severity` rather than assume every flag fits
 * that shape. */
export interface Flag {
  metric: string;
  value: unknown;
  threshold: unknown;
  severity?: "severe" | "moderate";
  recommendation: string;
  exercises?: FlagExercise[];
}

export type RearMetricTier = "low" | "moderate" | "high";

export interface RearMetricConfidence {
  score: number;
  tier: RearMetricTier;
}

/** One frontal-plane metric for one leg (backend/rear_metrics.py). Value is a
 * pattern indicator, not a precise angle — see `disclaimer` and
 * `error_margin_deg` (null where no validated margin exists). */
export type RearMetric =
  | {
      available: true;
      value_deg: number;
      pattern: string;
      cycles_used: number;
      error_margin_deg: number | null;
      confidence: RearMetricConfidence;
      disclaimer: string;
    }
  | { available: false; reason: string };

export interface RearLeg {
  cycles_detected: number;
  cycles_usable: number;
  reportable: boolean;
  hip_drop: RearMetric;
  pronation: RearMetric;
  knee_valgus: RearMetric;
}

export type RearSymmetry =
  | {
      available: true;
      score: number;
      band: string;
      components: Record<string, number>;
      confidence: RearMetricConfidence;
      disclaimer: string;
    }
  | { available: false; reason: string };

/** results.rear_view, as merged in by backend/results_schema.py. Only `status`
 * is guaranteed — a still-processing or failed rear video has no legs/symmetry
 * at all (see backend/schema/results.schema.json's rear_view_pending/_failed).
 * Scoped to what the UI renders today, not a full mirror of the schema
 * (e.g. `curves`, per-metric `window_pct` aren't typed since nothing reads them yet). */
export interface RearView {
  status: "ok" | "low_confidence" | "insufficient_data" | "processing" | "failed";
  error?: string;
  confidence_gate?: {
    status: string;
    reason: string | null;
    user_message: string | null;
  };
  legs?: { left: RearLeg; right: RearLeg };
  symmetry?: RearSymmetry;
}

export interface RunListItem {
  run_id: string;
  created_at: string;
  recorded_at: string | null;
  cadence_avg: number | null;
  vertical_osc_avg_cm: number | null;
  knee_angle_strike_avg_deg: number | null;
  flags_count: number;
}

export interface RunListResponse {
  total: number;
  items: RunListItem[];
}

export interface RunDetail {
  run_id: string;
  created_at: string;
  recorded_at: string | null;
  height_cm: number;
  status: string;
  results: {
    schema_version?: number;
    summary?: Record<string, unknown>;
    flags?: Flag[];
    strides?: unknown[];
    meta?: Record<string, unknown>;
    rear_view?: RearView | null;
  } | null;
  annotated_video_url: string | null;
  dashboard_image_url: string | null;
  // Skeleton-overlay rear-view video, set only once a rear video exists and
  // has finished processing (mirrors annotated_video_url's gating).
  rear_video_url: string | null;
  error_message: string | null;
}

export interface ConsentStatus {
  policy_version: string;
  consented: boolean;
  consented_at: string | null;
}

export interface BillingStatus {
  tier: string;
  status: string | null;
  is_pro: boolean;
  trial_end: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  free_scans_used: number;
  free_scans_limit: number;
  bonus_scans: number;
  referral_code: string;
  referral_link: string;
}

/** Error thrown by fetchApi/createRunWithProgress. `code` is the machine-readable
 * error code the backend attaches to billing-gate responses (e.g. "free_scan_used"),
 * so callers can branch on it (e.g. to show an upgrade modal) instead of string-matching. */
export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function parseErrorDetail(body: unknown, fallback: string): { message: string; code?: string } {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (detail && typeof detail === "object") {
    const d = detail as { code?: string; message?: string };
    return { message: d.message || fallback, code: d.code };
  }
  if (typeof detail === "string") return { message: detail };
  return { message: fallback };
}

async function fetchApi<T>(
  path: string,
  options?: RequestInit & { cache?: RequestCache },
  token?: string,
  anonId?: string,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const { cache, ...restOptions } = options ?? {};
  const res = await fetch(url, {
    ...restOptions,
    ...(cache !== undefined && { cache }),
    headers: {
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : anonId
          ? { "X-Anon-Id": anonId }
          : {}),
      ...restOptions.headers,
    },
  });
  if (!res.ok) {
    let parsed: { message: string; code?: string } = { message: `HTTP ${res.status}` };
    try {
      parsed = parseErrorDetail(await res.json(), `HTTP ${res.status}`);
    } catch {
      // response wasn't JSON; fall back to the generic HTTP status message
    }
    throw new ApiError(parsed.message, res.status, parsed.code);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Create a run. Requires either a valid Clerk Bearer token or an anon id
 * (see backend/anon.py — anonymous visitors get one free scan). */
export async function createRun(
  formData: FormData,
  token?: string,
  anonId?: string,
): Promise<RunCreated> {
  return fetchApi<RunCreated>("/api/runs", { method: "POST", body: formData }, token, anonId);
}

/**
 * Create a run with XHR so upload byte progress is available.
 * onUploadProgress is called with 0–100 as bytes are sent.
 */
export function createRunWithProgress(
  formData: FormData,
  token: string | undefined,
  anonId: string | undefined,
  onUploadProgress: (pct: number) => void,
): Promise<RunCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/runs`);
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    } else if (anonId) {
      xhr.setRequestHeader("X-Anon-Id", anonId);
    }

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        onUploadProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as RunCreated);
        } catch {
          reject(new Error("Invalid response from server"));
        }
      } else {
        let parsed: { message: string; code?: string } = { message: `HTTP ${xhr.status}` };
        try {
          parsed = parseErrorDetail(JSON.parse(xhr.responseText), `HTTP ${xhr.status}`);
        } catch {
          // response wasn't JSON; fall back to the generic HTTP status message
        }
        reject(new ApiError(parsed.message, xhr.status, parsed.code));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Upload failed")));
    xhr.addEventListener("abort", () => reject(new Error("Upload cancelled")));

    xhr.send(formData);
  });
}

/**
 * Add an optional rear-view video to an existing run, with XHR upload progress
 * (see createRunWithProgress — same reasoning: fetch has no upload progress
 * event). Requires ownership: a valid Clerk Bearer token, or (for a run made
 * without an account) the anon id that created it — POST /api/runs/{id}/rear-video
 * 404s otherwise, without leaking whether the run exists (see backend/main.py).
 * 409 (code "rear_video_exists") means one's already attached and isn't in a
 * failed state; a failed one may be retried by calling this again.
 */
export function addRearVideoWithProgress(
  runId: string,
  formData: FormData,
  token: string | undefined,
  anonId: string | undefined,
  onUploadProgress: (pct: number) => void,
): Promise<RearVideoCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/runs/${runId}/rear-video`);
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    } else if (anonId) {
      xhr.setRequestHeader("X-Anon-Id", anonId);
    }

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        onUploadProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as RearVideoCreated);
        } catch {
          reject(new Error("Invalid response from server"));
        }
      } else {
        let parsed: { message: string; code?: string } = { message: `HTTP ${xhr.status}` };
        try {
          parsed = parseErrorDetail(JSON.parse(xhr.responseText), `HTTP ${xhr.status}`);
        } catch {
          // response wasn't JSON; fall back to the generic HTTP status message
        }
        reject(new ApiError(parsed.message, xhr.status, parsed.code));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Upload failed")));
    xhr.addEventListener("abort", () => reject(new Error("Upload cancelled")));

    xhr.send(formData);
  });
}

/** Poll run status. Public — no auth required, but pass whatever credential
 * the caller has (token if signed in, else anon id) so `is_owner` resolves
 * correctly; omitting both still works, `is_owner` just comes back false. */
export async function getRunStatus(id: string, token?: string, anonId?: string): Promise<RunStatus> {
  return fetchApi<RunStatus>(`/api/runs/${id}/status`, undefined, token, anonId);
}

/** Get full run detail. Public — anyone with the UUID can view (enables sharing). */
export async function getRun(id: string): Promise<RunDetail> {
  return fetchApi<RunDetail>(`/api/runs/${id}`, { cache: "no-store" });
}

/** Same as getRun, but resolves to null instead of throwing — for image-generation
 * routes (opengraph-image, share-card) that render a fallback rather than erroring. */
export async function getRunOrNull(id: string): Promise<RunDetail | null> {
  try {
    return await getRun(id);
  } catch {
    return null;
  }
}

/** List runs for the authenticated user. Requires a valid Clerk Bearer token. */
export async function listRuns(
  params?: { limit?: number; offset?: number },
  token?: string,
): Promise<RunListResponse> {
  const qs = new URLSearchParams();
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const query = qs.toString() ? `?${qs}` : "";
  return fetchApi<RunListResponse>(`/api/runs${query}`, undefined, token);
}

/** Delete a run. Requires ownership: a valid Clerk Bearer token, or (for a
 * scan made without an account) the anon id that created it. */
export async function deleteRun(id: string, token?: string, anonId?: string): Promise<boolean> {
  try {
    await fetchApi<void>(`/api/runs/${id}`, { method: "DELETE" }, token, anonId);
    return true;
  } catch {
    return false;
  }
}

/** Whether the current user (or anonymous visitor) has accepted the current
 * privacy-policy version. */
export async function getConsentStatus(token?: string, anonId?: string): Promise<ConsentStatus> {
  return fetchApi<ConsentStatus>("/api/consent", undefined, token, anonId);
}

/** Record consent to the given policy version. 409 (code "stale_policy_version")
 * means the policy changed since the page loaded — reload and re-present it.
 * `ageConfirmed` is the anonymous-only "I'm 18 or older" checkbox — required
 * (400 "age_confirmation_required") when consenting without a token. */
export async function recordConsent(
  policyVersion: string,
  token?: string,
  anonId?: string,
  ageConfirmed?: boolean,
): Promise<ConsentStatus> {
  return fetchApi<ConsentStatus>(
    "/api/consent",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy_version: policyVersion, age_confirmed: !!ageConfirmed }),
    },
    token,
    anonId,
  );
}

/** Merge an anonymous visitor's run(s)/consent/free-scan usage into the now
 * signed-in user's account. Idempotent — safe to call more than once. */
export async function claimAnonymousRuns(
  anonId: string,
  token: string,
): Promise<{ claimed_runs: number; consent_claimed: boolean; free_scans_merged: number }> {
  return fetchApi(
    "/api/runs/claim",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ anon_id: anonId }),
    },
    token,
  );
}

/** Current user's tier/trial/scan-usage/referral status. Requires a valid Clerk Bearer token. */
export async function getBillingStatus(token: string): Promise<BillingStatus> {
  return fetchApi<BillingStatus>("/api/billing/status", undefined, token);
}

/** Start a Stripe Checkout session for the given plan; returns the URL to redirect to. */
export async function createCheckoutSession(
  plan: "monthly" | "yearly",
  token: string,
): Promise<{ url: string }> {
  return fetchApi<{ url: string }>(
    "/api/billing/checkout",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan }),
    },
    token,
  );
}

/** Open the Stripe Customer Portal for the current user; returns the URL to redirect to. */
export async function createPortalSession(token: string): Promise<{ url: string }> {
  return fetchApi<{ url: string }>("/api/billing/portal", { method: "POST" }, token);
}

/** Download a run's branded PDF report (Pro-gated). Requires a valid Clerk Bearer token. */
export async function downloadRunReportPdf(runId: string, token: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/report.pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    let parsed: { message: string; code?: string } = { message: `HTTP ${res.status}` };
    try {
      parsed = parseErrorDetail(await res.json(), `HTTP ${res.status}`);
    } catch {
      // response wasn't JSON; fall back to the generic HTTP status message
    }
    throw new ApiError(parsed.message, res.status, parsed.code);
  }
  return res.blob();
}

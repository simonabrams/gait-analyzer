// Video uploads go from the browser directly to the Render backend (createRun uses
// API_BASE below). They never go through a Next.js API route, so Vercel's 4.5MB
// payload limit does not apply. Keep uploads pointing at the backend URL only.

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");
if (!API_BASE) {
  throw new Error("NEXT_PUBLIC_API_URL is not set. Set it in .env.local (dev) or Vercel env (production).");
}

/** Replace with a real sample run ID when you have an analysis to showcase. */
export const SAMPLE_RUN_ID = "aba77d1f-2c19-4d10-808c-f4f7fd7b90e3";

export interface RunCreated {
  run_id: string;
  status: string;
}

export interface RunStatus {
  status: string;
  progress: number;
  preprocessing_warning: string | null;
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
    summary?: Record<string, unknown>;
    flags?: Array<{ metric: string; value: unknown; threshold: unknown; recommendation: string }>;
    strides?: unknown[];
    meta?: Record<string, unknown>;
  } | null;
  annotated_video_url: string | null;
  dashboard_image_url: string | null;
  error_message: string | null;
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
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const { cache, ...restOptions } = options ?? {};
  const res = await fetch(url, {
    ...restOptions,
    ...(cache !== undefined && { cache }),
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
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

/** Create a run. Requires a valid Clerk Bearer token. */
export async function createRun(formData: FormData, token: string): Promise<RunCreated> {
  return fetchApi<RunCreated>("/api/runs", { method: "POST", body: formData }, token);
}

/**
 * Create a run with XHR so upload byte progress is available.
 * onUploadProgress is called with 0–100 as bytes are sent.
 */
export function createRunWithProgress(
  formData: FormData,
  token: string,
  onUploadProgress: (pct: number) => void,
): Promise<RunCreated> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/runs`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

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

/** Poll run status. Public — no auth required. */
export async function getRunStatus(id: string): Promise<RunStatus> {
  return fetchApi<RunStatus>(`/api/runs/${id}/status`);
}

/** Get full run detail. Public — anyone with the UUID can view (enables sharing). */
export async function getRun(id: string): Promise<RunDetail> {
  return fetchApi<RunDetail>(`/api/runs/${id}`, { cache: "no-store" });
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

/** Delete a run. Requires a valid Clerk Bearer token and ownership. */
export async function deleteRun(id: string, token: string): Promise<boolean> {
  try {
    await fetchApi<void>(`/api/runs/${id}`, { method: "DELETE" }, token);
    return true;
  } catch {
    return false;
  }
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

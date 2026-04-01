// Video uploads go from the browser directly to the Render backend (createRun uses
// API_BASE below). They never go through a Next.js API route, so Vercel's 4.5MB
// payload limit does not apply. Keep uploads pointing at the backend URL only.

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");
if (!API_BASE) {
  throw new Error("NEXT_PUBLIC_API_URL is not set. Set it in .env.local (dev) or Vercel env (production).");
}

/** Replace with a real sample run ID when you have an analysis to showcase. */
export const SAMPLE_RUN_ID = "0550b69f-c76b-44e1-b785-961232264a19";

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
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Create a run. Requires a valid Clerk Bearer token. */
export async function createRun(formData: FormData, token: string): Promise<RunCreated> {
  return fetchApi<RunCreated>("/api/runs", { method: "POST", body: formData }, token);
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

// ACTION REQUIRED: Add your Vercel deployment URL to the CORS allowed origins
// in backend/main.py after first deploy.
// Format: https://runlens.vercel.app or your custom domain.

// Video uploads go from the browser directly to the Render backend (createRun uses
// API_BASE below). They never go through a Next.js API route, so Vercel’s 4.5MB
// payload limit does not apply. Keep uploads pointing at the backend URL only.

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");
if (!API_BASE) {
  throw new Error("NEXT_PUBLIC_API_URL is not set. Set it in .env.local (dev) or Vercel env (production).");
}

/** Replace with a real sample run ID when you have an analysis to showcase. */
export const SAMPLE_RUN_ID = "ab242812-582f-4107-b41c-0011087cd667";

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

function apiUrl(path: string, directToBackend: boolean): string {
  if (directToBackend) return `${API_BASE}${path}`;
  if (typeof window !== "undefined") return path;
  return `${API_BASE}${path}`;
}

async function fetchApi<T>(
  path: string,
  options?: RequestInit & { cache?: RequestCache },
  directToBackend = false
): Promise<T> {
  const url = apiUrl(path, directToBackend);
  const { cache, ...restOptions } = options ?? {};
  const res = await fetch(url, {
    ...restOptions,
    ...(cache !== undefined && { cache }),
    headers: {
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

export async function createRun(formData: FormData): Promise<RunCreated> {
  return fetchApi<RunCreated>("/api/runs", {
    method: "POST",
    body: formData,
  }, true);
}

export async function getRunStatus(id: string): Promise<RunStatus> {
  return fetchApi<RunStatus>(`/api/runs/${id}/status`, undefined, true);
}

export async function getRun(id: string): Promise<RunDetail> {
  return fetchApi<RunDetail>(`/api/runs/${id}`, { cache: "no-store" }, true);
}

export async function listRuns(): Promise<RunListItem[]> {
  return fetchApi<RunListItem[]>("/api/runs", undefined, true);
}

export async function deleteRun(id: string): Promise<boolean> {
  try {
    await fetchApi<void>(`/api/runs/${id}`, { method: "DELETE" }, true);
    return true;
  } catch {
    return false;
  }
}

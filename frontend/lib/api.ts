const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface RunCreated {
  run_id: string;
  status: string;
}

export interface RunStatus {
  status: string;
  progress: number;
}

export interface RunListItem {
  run_id: string;
  created_at: string;
  cadence_avg: number | null;
  vertical_osc_avg_cm: number | null;
  knee_angle_strike_avg_deg: number | null;
  flags_count: number;
}

export interface RunDetail {
  run_id: string;
  created_at: string;
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
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
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
  });
}

export async function getRunStatus(id: string): Promise<RunStatus> {
  return fetchApi<RunStatus>(`/api/runs/${id}/status`);
}

export async function getRun(id: string): Promise<RunDetail> {
  return fetchApi<RunDetail>(`/api/runs/${id}`);
}

export async function listRuns(): Promise<RunListItem[]> {
  return fetchApi<RunListItem[]>("/api/runs");
}

export async function deleteRun(id: string): Promise<void> {
  return fetchApi<void>(`/api/runs/${id}`, { method: "DELETE" });
}

/** Client-generated anonymous visitor id, used to grant a free scan and track
 * consent before signup. Format `anon:<uuid>` matches backend/anon.py's regex. */
const KEY = "gait_anon_id";

export function getOrCreateAnonId(): string {
  const existing = localStorage.getItem(KEY);
  if (existing) return existing;
  const id = `anon:${crypto.randomUUID()}`;
  localStorage.setItem(KEY, id);
  return id;
}

export function getStoredAnonId(): string | null {
  return localStorage.getItem(KEY);
}

export function clearAnonId(): void {
  localStorage.removeItem(KEY);
}

/** Run IDs created anonymously from this browser, so the run detail page can
 * offer self-serve deletion to the visitor who made them (and only them) —
 * without an account, there's no /runs history to find them from otherwise. */
const RUNS_KEY = "gait_anon_run_ids";
const MAX_REMEMBERED_RUNS = 50;

export function rememberAnonRun(runId: string): void {
  const ids = _readAnonRunIds();
  if (ids.includes(runId)) return;
  ids.push(runId);
  // Cap the list so it can't grow unbounded over a long-lived browser profile.
  while (ids.length > MAX_REMEMBERED_RUNS) ids.shift();
  localStorage.setItem(RUNS_KEY, JSON.stringify(ids));
}

export function forgetAnonRun(runId: string): void {
  const ids = _readAnonRunIds().filter((id) => id !== runId);
  localStorage.setItem(RUNS_KEY, JSON.stringify(ids));
}

export function hasAnonRun(runId: string): boolean {
  return _readAnonRunIds().includes(runId);
}

function _readAnonRunIds(): string[] {
  try {
    const raw = localStorage.getItem(RUNS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === "string") : [];
  } catch {
    return [];
  }
}

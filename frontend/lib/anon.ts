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

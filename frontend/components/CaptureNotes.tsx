export interface CaptureNote {
  code: string;
  message: string;
}

/** "For your next clip" filming tips from what the analysis noticed about
 * the footage (backend: rear_confidence.capture_notes for the rear view,
 * view_check.side_capture_notes for the side view). Informational, not a
 * warning: the results already account for them. */
export default function CaptureNotes({ title, notes }: { title: string; notes: CaptureNote[] }) {
  if (notes.length === 0) return null;
  return (
    <div className="rounded-xl border border-blue-700/30 bg-blue-950/30 px-5 py-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-blue-300 mb-2">{title}</p>
      <ul className="space-y-1.5">
        {notes.map((n) => (
          <li key={n.code} className="text-sm text-blue-100/90 leading-relaxed flex gap-2">
            <span aria-hidden className="text-blue-400">•</span>
            <span>{n.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Capture notes out of an untyped results.meta (side view), dropping
 * anything malformed. */
export function captureNotesFrom(meta: Record<string, unknown> | undefined): CaptureNote[] {
  const raw = meta?.capture_notes;
  if (!Array.isArray(raw)) return [];
  return raw.filter(
    (n): n is CaptureNote =>
      !!n && typeof n === "object" && typeof (n as CaptureNote).code === "string" &&
      typeof (n as CaptureNote).message === "string",
  );
}

import type { RearSymmetry } from "@/lib/api";

/** Rear metrics the results page shows and scores. Everything else in a
 * stored rear_view is hidden, including in the left/right balance score:
 * - pronation: hidden since metrics_version 2.
 * - hip_drop: hidden since metrics_version 3. On real clips the hip landmarks
 *   tilt the opposite way to a pelvic drop (see backend/rear_metrics.py's
 *   EXPERIMENTAL_METRICS), so it read 0 deg / meaningless values.
 * Runs analysed before either change still carry those metrics and a balance
 * score that includes them, so the score is rebuilt here from its per-metric
 * components rather than trusting the stored total. */
export const SHOWN_REAR_METRICS = ["knee_valgus", "step_width"] as const;

// Mirrors backend/rear_confidence.py SYMMETRY_BAND_SYMMETRIC_MIN / _MILD_MIN.
const BAND_SYMMETRIC_MIN = 85;
const BAND_MILD_MIN = 65;

export interface DisplayedBalance {
  score: number;
  band: "symmetric" | "mild_asymmetry" | "notable_asymmetry";
}

/** The balance score over the shown metrics only, or null when fewer than
 * two of them are available on both legs (same minimum as the backend). */
export function displayedBalance(symmetry: RearSymmetry | undefined | null): DisplayedBalance | null {
  if (!symmetry?.available) return null;
  const parts = SHOWN_REAR_METRICS.map((m) => symmetry.components[m]).filter(
    (v): v is number => typeof v === "number",
  );
  if (parts.length < 2) return null;
  const score = Math.round(parts.reduce((a, b) => a + b, 0) / parts.length);
  const band =
    score >= BAND_SYMMETRIC_MIN ? "symmetric" : score >= BAND_MILD_MIN ? "mild_asymmetry" : "notable_asymmetry";
  return { score, band };
}

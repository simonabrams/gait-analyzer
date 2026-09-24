// Single source of truth for the Good/Watch/Focus status system — SIDE-VIEW
// ONLY. Every badge must come from the same rule as the flag it represents
// (results.flags, from backend/heuristics.py's real, threshold-validated
// checks), never a separately-invented score — that's how the old
// FeedbackCards.tsx's computeScore() and a flag's actual severity could
// silently disagree.
//
// Deliberately NOT used for rear-view metrics: rear has no validated
// performance thresholds, only pattern labels (typical/elevated/pronounced)
// and confidence tiers (measurement reliability, a different axis entirely —
// see backend/rear_confidence.py). Collapsing the two would misrepresent
// rear data with more certainty than we actually have; keep them visually
// distinct (see RearViewSection.tsx).

import type { Flag } from "@/lib/api";

export type GaitStatus = "good" | "watch" | "focus";

export const STATUS_LABEL: Record<GaitStatus, string> = {
  good: "Good",
  watch: "Watch",
  focus: "Focus",
};

export const STATUS_BADGE_CLASSES: Record<GaitStatus, string> = {
  good: "bg-primary/15 text-primary border border-primary/30",
  watch: "bg-amber-400/15 text-amber-400 border border-amber-400/30",
  focus: "bg-red-400/15 text-red-400 border border-red-400/30",
};

export const STATUS_TEXT_CLASSES: Record<GaitStatus, string> = {
  good: "text-primary",
  watch: "text-amber-400",
  focus: "text-red-400",
};

type FindingFlag = Flag & { severity: "severe" | "moderate" };

/** Only flags with a `severity` are performance findings. The
 * `cadence_confidence` flag (backend/heuristics.py's
 * _check_cadence_confidence) has none — it's a measurement-reliability
 * warning, not a "this is bad" judgment, and doesn't fit the G/W/F shape
 * at all (no target/current to show). */
export function isFindingFlag(flag: Flag): flag is FindingFlag {
  return flag.severity === "severe" || flag.severity === "moderate";
}

export function findingFlags(flags: Flag[] | undefined): FindingFlag[] {
  return (flags ?? []).filter(isFindingFlag);
}

/** Worst first: severe before moderate. Stable for equal severity. */
export function sortBySeverity(flags: FindingFlag[]): FindingFlag[] {
  const rank: Record<FindingFlag["severity"], number> = { severe: 0, moderate: 1 };
  return [...flags].sort((a, b) => rank[a.severity] - rank[b.severity]);
}

/** Status for one metric tile. `metricNames` should include both the flag's
 * own name and any merged-flag name it can appear under (e.g. cadence and
 * overstriding both fold into "stride_and_cadence" when both are flagged at
 * once — see heuristics.py's _resolve_flag_conflicts) — a tile is Watch/Focus
 * whenever either form is present, Good otherwise (no flag = within target). */
export function statusForMetric(flags: Flag[] | undefined, metricNames: string[]): GaitStatus {
  const match = findingFlags(flags).find((f) => metricNames.includes(f.metric));
  if (!match) return "good";
  return match.severity === "severe" ? "focus" : "watch";
}

const FLAG_LABELS: Record<string, string> = {
  cadence: "cadence",
  vertical_oscillation: "bounce",
  knee_flexion_at_strike: "knee drive",
  overstriding: "overstriding",
  trunk_lean: "posture",
  stride_and_cadence: "cadence and overstriding",
  cadence_confidence: "cadence confidence",
};

/** "overstriding" / "cadence and overstriding" — lowercase, for inline use in
 * generated prose; use humanFlagTitle for card headings instead. */
export function humanFlagLabel(metric: string): string {
  return FLAG_LABELS[metric] ?? metric.replace(/_/g, " ");
}

/** "Overstriding" / "Cadence & Overstriding" — capitalized, for card titles. */
export function humanFlagTitle(metric: string): string {
  const label = humanFlagLabel(metric).replace(/ and /g, " & ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

const FLAG_UNITS: Record<string, string> = {
  cadence: "spm",
  stride_and_cadence: "spm",
  vertical_oscillation: "cm",
  knee_flexion_at_strike: "°",
  overstriding: "cm",
  trunk_lean: "°",
};

export function formatFlagValue(value: unknown, metric: string): string {
  const n = Number(value);
  if (!isFinite(n)) return "";
  const unit = FLAG_UNITS[metric] ?? "";
  const rounded = Math.round(n * 10) / 10;
  return unit ? `${rounded} ${unit}` : String(rounded);
}

/** Per-metric source of the stride-level field + "is this stride within
 * target" predicate — mirrors backend/heuristics.py's per-check thresholds
 * (CADENCE_MIN_SPM, VERTICAL_OSC_MAX_CM, KNEE_FLEXION_MIN_DEG,
 * OVERSTRIDE_CM_THRESHOLD, TRUNK_LEAN_MAX_DEG). Used to build a real
 * "N of M strides over target" source line instead of a hardcoded one. */
export const FLAG_STRIDE_SOURCE: Record<string, { field: string; good: (v: number) => boolean }> = {
  cadence: { field: "cadence", good: (v) => v >= 170 },
  stride_and_cadence: { field: "cadence", good: (v) => v >= 170 },
  vertical_oscillation: { field: "vertical_osc_cm", good: (v) => v <= 10 },
  knee_flexion_at_strike: { field: "knee_angle_strike_deg", good: (v) => v >= 15 },
  overstriding: { field: "foot_strike_position_cm", good: (v) => v <= 10 },
  trunk_lean: { field: "trunk_lean_deg", good: (v) => v <= 15 },
};

// Gait metric targets — single source of truth for the thresholds used to
// score/color metrics across MetricCards, share cards, and progress charts.
// Mirrors backend/heuristics.py's CADENCE_MIN_SPM / VERTICAL_OSC_MAX_CM /
// KNEE_FLEXION_MIN_DEG constants; keep both in sync if targets change.

export const CADENCE_TARGET_SPM = 170;
export const VERTICAL_OSC_TARGET_CM = 10;
export const KNEE_DRIVE_TARGET_DEG = 15;

export const METRIC_TARGETS = {
  cadence: {
    key: "cadence_avg",
    label: "Cadence",
    unit: "SPM",
    target: CADENCE_TARGET_SPM,
    good: (v: number) => v >= CADENCE_TARGET_SPM,
    score: (v: number) => Math.min(Math.round((v / CADENCE_TARGET_SPM) * 100), 100),
  },
  bounce: {
    key: "vertical_osc_avg_cm",
    label: "Bounce",
    unit: "cm",
    target: VERTICAL_OSC_TARGET_CM,
    good: (v: number) => v <= VERTICAL_OSC_TARGET_CM,
    score: (v: number) =>
      v <= 0 ? 0 : Math.min(Math.round((VERTICAL_OSC_TARGET_CM / v) * 100), 100),
  },
  kneeDrive: {
    key: "knee_angle_strike_avg_deg",
    label: "Knee Drive",
    unit: "°",
    target: KNEE_DRIVE_TARGET_DEG,
    good: (v: number) => v >= KNEE_DRIVE_TARGET_DEG,
    score: (v: number) => Math.min(Math.round((v / KNEE_DRIVE_TARGET_DEG) * 100), 100),
  },
} as const;

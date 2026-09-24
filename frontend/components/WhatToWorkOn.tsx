"use client";

import { useState } from "react";
import type { Flag } from "@/lib/api";
import {
  FLAG_STRIDE_SOURCE,
  STATUS_BADGE_CLASSES,
  STATUS_LABEL,
  findingFlags,
  formatFlagValue,
  humanFlagTitle,
  sortBySeverity,
} from "@/lib/gaitStatus";

interface WhatToWorkOnProps {
  flags: Flag[] | undefined;
  strides: Array<Record<string, unknown>> | undefined;
}

/** Side-view findings only — replaces the old FeedbackCards on this page.
 * Rear-view patterns intentionally have no equivalent card here: rear has no
 * validated performance thresholds to generate a Good/Watch/Focus finding
 * from (see lib/gaitStatus.ts's header comment); they stay in the Rear View
 * section as pattern + confidence-tier, not as an actionable "fix this"
 * card with drills that would overstate how certain we are. */
export default function WhatToWorkOn({ flags, strides }: WhatToWorkOnProps) {
  const findings = sortBySeverity(findingFlags(flags)).filter((f) => f.metric !== "cadence_confidence");

  if (findings.length === 0) {
    return (
      <div className="bg-secondary border border-white/10 rounded-xl p-5 flex items-center gap-3">
        <div>
          <p className="text-sm font-medium text-white">Great form — nothing flagged</p>
          <p className="text-xs text-gray-400 mt-0.5">All measured metrics are within target ranges.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 items-start">
      {findings.map((f) => (
        <FindingCard key={f.metric} flag={f} strides={strides} />
      ))}
    </div>
  );
}

function sourceLine(flag: Flag, strides: Array<Record<string, unknown>> | undefined): string | null {
  const source = FLAG_STRIDE_SOURCE[flag.metric];
  if (!source || !strides?.length) return null;
  const values = strides
    .map((s) => s[source.field])
    .filter((v): v is number => typeof v === "number");
  if (values.length === 0) return null;
  const overCount = values.filter((v) => !source.good(v)).length;
  return `SIDE VIEW · ${overCount} OF ${values.length} STRIDES OVER TARGET`;
}

function FindingCard({ flag, strides }: { flag: Flag & { severity: "severe" | "moderate" }; strides: Array<Record<string, unknown>> | undefined }) {
  const [showDrills, setShowDrills] = useState(false);
  const status = flag.severity === "severe" ? "focus" : "watch";
  const source = sourceLine(flag, strides);
  const exercises = flag.exercises ?? [];

  return (
    <div id={`finding-${flag.metric}`} className="bg-secondary border border-white/10 rounded-xl p-5 flex flex-col gap-3 scroll-mt-24">
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-white">{humanFlagTitle(flag.metric)}</span>
        <span className={`text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded shrink-0 ${STATUS_BADGE_CLASSES[status]}`}>
          {STATUS_LABEL[status]}
        </span>
      </div>

      {source && (
        <p className="font-mono text-[11px] tracking-[0.08em] text-gray-500">{source}</p>
      )}

      <div className="flex items-center gap-4 text-xs">
        <div>
          <p className="text-gray-500 mb-0.5">Current</p>
          <p className="text-red-400 font-mono font-semibold">{formatFlagValue(flag.value, flag.metric)}</p>
        </div>
        <div>
          <p className="text-gray-500 mb-0.5">Target</p>
          <p className="text-gray-300 font-mono font-semibold">{targetPrefix(flag.metric)}{formatFlagValue(flag.threshold, flag.metric)}</p>
        </div>
      </div>

      <p className="text-xs text-gray-300 leading-relaxed">{flag.recommendation}</p>

      {exercises.length > 0 && (
        <div className="border-t border-white/10 pt-3">
          <button
            type="button"
            onClick={() => setShowDrills((v) => !v)}
            className="text-xs font-medium text-primary hover:underline"
          >
            {showDrills ? "Hide drills" : `Show ${exercises.length} drills`}
          </button>
          {showDrills && (
            <div className="space-y-2.5 mt-3">
              {exercises.map((ex) => (
                <div key={ex.name}>
                  <p className="text-xs font-semibold text-white">{ex.name}</p>
                  <p className="text-xs text-gray-400 leading-relaxed mt-0.5">{ex.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function targetPrefix(metric: string): string {
  const source = FLAG_STRIDE_SOURCE[metric];
  if (!source) return "";
  return source.good(1e9) ? "≥" : "≤";
}

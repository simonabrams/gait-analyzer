import { ImageResponse } from "next/og";
import { getRun } from "@/lib/api";

export const alt = "Run Report — Runlens";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

function MetricPill({
  label,
  value,
  good,
}: {
  label: string;
  value: string;
  good: boolean | null;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        background: "#1A1A1A",
        border: `1px solid ${good === true ? "rgba(0,200,150,0.3)" : good === false ? "rgba(245,158,11,0.3)" : "rgba(255,255,255,0.1)"}`,
        borderRadius: "16px",
        padding: "28px 40px",
        minWidth: "220px",
      }}
    >
      <div
        style={{
          fontSize: "13px",
          fontWeight: "600",
          color: "#00C896",
          letterSpacing: "3px",
          textTransform: "uppercase",
          marginBottom: "12px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "48px",
          fontWeight: "800",
          color: "#ffffff",
          lineHeight: 1,
        }}
      >
        {value}
      </div>
    </div>
  );
}

export default async function Image({ params }: { params: { id: string } }) {
  let run;
  try {
    run = await getRun(params.id);
  } catch {
    run = null;
  }

  const summary = run?.results?.summary;
  const flags = run?.results?.flags ?? [];

  const cadenceVal = summary?.cadence_avg != null ? Number(summary.cadence_avg) : null;
  const vertOscVal = summary?.vertical_osc_avg_cm != null ? Number(summary.vertical_osc_avg_cm) : null;
  const kneeVal = summary?.knee_angle_strike_avg_deg != null ? Number(summary.knee_angle_strike_avg_deg) : null;

  const metrics = [
    {
      label: "Cadence",
      value: cadenceVal != null ? `${cadenceVal} SPM` : "—",
      good: cadenceVal != null ? cadenceVal >= 170 : null,
    },
    {
      label: "V. Oscillation",
      value: vertOscVal != null ? `${vertOscVal} cm` : "—",
      good: vertOscVal != null ? vertOscVal <= 10 : null,
    },
    {
      label: "Knee Angle",
      value: kneeVal != null ? `${kneeVal}°` : "—",
      good: kneeVal != null ? kneeVal >= 15 : null,
    },
  ];

  const flagCount = flags.length;
  const statusColor = flagCount === 0 ? "#00C896" : "#f59e0b";
  const statusText =
    flagCount === 0 ? "✓  No issues flagged" : `${flagCount} issue${flagCount !== 1 ? "s" : ""} flagged`;

  return new ImageResponse(
    (
      <div
        style={{
          background: "#0F0F0F",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "60px 72px",
          fontFamily: "system-ui, sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Teal glow */}
        <div
          style={{
            position: "absolute",
            top: "-80px",
            right: "-80px",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(0,200,150,0.12) 0%, rgba(0,200,150,0) 70%)",
          }}
        />

        {/* Header */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div
            style={{
              fontSize: "14px",
              fontWeight: "700",
              color: "#00C896",
              letterSpacing: "3px",
              textTransform: "uppercase",
            }}
          >
            Analysis Complete
          </div>
          <div
            style={{
              fontSize: "52px",
              fontWeight: "800",
              color: "#ffffff",
              letterSpacing: "-1px",
              lineHeight: 1,
            }}
          >
            Your Run Report
          </div>
        </div>

        {/* Metrics row */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            gap: "20px",
            justifyContent: "center",
          }}
        >
          {metrics.map((m) => (
            <MetricPill key={m.label} label={m.label} value={m.value} good={m.good} />
          ))}
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div
            style={{
              fontSize: "20px",
              fontWeight: "600",
              color: statusColor,
            }}
          >
            {statusText}
          </div>
          <div
            style={{
              fontSize: "18px",
              color: "#4b5563",
              fontWeight: "500",
            }}
          >
            runlens.io
          </div>
        </div>

        {/* Bottom bar */}
        <div
          style={{
            position: "absolute",
            bottom: "0",
            left: "0",
            right: "0",
            height: "4px",
            background: "#00C896",
          }}
        />
      </div>
    ),
    { ...size },
  );
}

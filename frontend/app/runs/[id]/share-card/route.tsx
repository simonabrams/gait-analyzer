import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";
import { getRunOrNull } from "@/lib/api";
import { computeArcGeometry, RING_GOOD_COLOR, RING_WARN_COLOR } from "@/lib/arcRing";
import { METRIC_TARGETS } from "@/lib/metricTargets";

export const runtime = "nodejs";

const SIZE = { width: 1080, height: 1180 };

const HERO = {
  label: METRIC_TARGETS.cadence.label,
  key: METRIC_TARGETS.cadence.key,
  unit: METRIC_TARGETS.cadence.unit,
  good: METRIC_TARGETS.cadence.good,
  score: METRIC_TARGETS.cadence.score,
};

const SECONDARY = [
  {
    label: METRIC_TARGETS.bounce.label,
    key: METRIC_TARGETS.bounce.key,
    unit: METRIC_TARGETS.bounce.unit,
    good: METRIC_TARGETS.bounce.good,
  },
  {
    label: METRIC_TARGETS.kneeDrive.label,
    key: METRIC_TARGETS.kneeDrive.key,
    unit: METRIC_TARGETS.kneeDrive.unit,
    good: METRIC_TARGETS.kneeDrive.good,
  },
];

function HeroRing({ score, value, unit, good }: { score: number; value: string; unit: string; good: boolean | null }) {
  const r = 150;
  const cx = 170;
  const cy = 170;
  const { circumference, arcLength, fillLength } = computeArcGeometry(r, score);
  const color = good === false ? RING_WARN_COLOR : RING_GOOD_COLOR;

  return (
    <div style={{ position: "relative", width: "340px", height: "340px", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg width="340" height="340" viewBox="0 0 340 340" style={{ position: "absolute", transform: "rotate(135deg)" }}>
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#1f1f1f"
          strokeWidth="20"
          strokeDasharray={`${arcLength} ${circumference - arcLength}`}
          strokeLinecap="round"
        />
        {fillLength > 0 && (
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="20"
            strokeDasharray={`${fillLength} ${circumference - fillLength}`}
            strokeLinecap="round"
          />
        )}
      </svg>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ fontSize: "104px", fontWeight: 800, color: "#ffffff", lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: "26px", fontWeight: 600, color: "#9ca3af", marginTop: "4px" }}>{unit}</div>
      </div>
    </div>
  );
}

function SecondaryStat({ label, value, good }: { label: string; value: string; good: boolean | null }) {
  const color = good === false ? "#f59e0b" : good === true ? "#00C896" : "#6b7280";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "20px",
        background: "#161616",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "18px",
        padding: "26px 30px",
        width: "100%",
      }}
    >
      <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: color, flexShrink: 0 }} />
      <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
        <div style={{ fontSize: "17px", fontWeight: 600, color: "#9ca3af", letterSpacing: "1.5px", textTransform: "uppercase" }}>
          {label}
        </div>
      </div>
      <div style={{ fontSize: "34px", fontWeight: 800, color: "#ffffff" }}>{value}</div>
    </div>
  );
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const run = await getRunOrNull(id);

  const summary = run?.results?.summary;
  const flags = run?.results?.flags ?? [];
  // Share cards are a highlight reel, not a diagnostic report — only celebrate
  // clean runs here. Flagged issues stay on the in-app report page.
  const showCleanStatus = flags.length === 0 && summary != null;

  const heroRaw = summary?.[HERO.key];
  const heroVal = heroRaw != null ? Number(heroRaw) : null;
  const hero = {
    value: heroVal != null ? String(heroRaw) : "—",
    score: heroVal != null ? HERO.score(heroVal) : 0,
    good: heroVal != null ? HERO.good(heroVal) : null,
  };

  const secondary = SECONDARY.map((m) => {
    const raw = summary?.[m.key];
    const numVal = raw != null ? Number(raw) : null;
    return {
      label: m.label,
      value: numVal != null ? `${raw}${m.unit ? ` ${m.unit}` : ""}` : "—",
      good: numVal != null ? m.good(numVal) : null,
    };
  });

  const analyzedDate = run?.created_at
    ? new Date(run.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : null;

  return new ImageResponse(
    (
      <div
        style={{
          background: "#0F0F0F",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          padding: "64px 64px 56px",
          fontFamily: "system-ui, sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "-140px",
            right: "-140px",
            width: "480px",
            height: "480px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(0,200,150,0.14) 0%, rgba(0,200,150,0) 70%)",
          }}
        />

        {/* Brand row */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                background: "#00C896",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "20px",
                fontWeight: 800,
                color: "#0F0F0F",
              }}
            >
              R
            </div>
            <div style={{ fontSize: "24px", fontWeight: 800, color: "#ffffff", letterSpacing: "-0.5px" }}>
              Runlens
            </div>
          </div>
          {analyzedDate && (
            <div style={{ fontSize: "18px", color: "#6b7280", fontWeight: 500 }}>{analyzedDate}</div>
          )}
        </div>

        {/* Title */}
        <div style={{ display: "flex", flexDirection: "column", marginTop: "36px" }}>
          <div
            style={{
              fontSize: "16px",
              fontWeight: 700,
              color: "#00C896",
              letterSpacing: "3px",
              textTransform: "uppercase",
            }}
          >
            Run Report
          </div>
          <div style={{ fontSize: "50px", fontWeight: 800, color: "#ffffff", letterSpacing: "-1px", lineHeight: 1.1, marginTop: "6px" }}>
            My Gait Analysis
          </div>
        </div>

        {/* Hero metric */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "32px" }}>
          <HeroRing score={hero.score} value={hero.value} unit={HERO.unit} good={hero.good} />
          <div
            style={{
              fontSize: "20px",
              fontWeight: 600,
              color: "#00C896",
              letterSpacing: "3px",
              textTransform: "uppercase",
              marginTop: "8px",
            }}
          >
            {HERO.label}
          </div>
        </div>

        {/* Secondary stats */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "44px" }}>
          {secondary.map((s) => (
            <SecondaryStat key={s.label} {...s} />
          ))}
        </div>

        {/* Status — only shown for clean runs; flagged issues stay in-app */}
        {showCleanStatus && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "16px",
              padding: "22px 26px",
              marginTop: "32px",
            }}
          >
            <div
              style={{
                width: "30px",
                height: "30px",
                borderRadius: "50%",
                background: "#00C896",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16">
                <path
                  d="M3 8.5L6.2 11.5L13 4"
                  fill="none"
                  stroke="#0F0F0F"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div style={{ fontSize: "24px", fontWeight: 600, color: "#00C896" }}>No issues flagged</div>
          </div>
        )}

        {/* Footer */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", marginTop: showCleanStatus ? "40px" : "auto", paddingTop: showCleanStatus ? 0 : "32px" }}>
          <div style={{ fontSize: "18px", color: "#4b5563", fontWeight: 500 }}>runlens.io</div>
        </div>

        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: "6px",
            background: "#00C896",
          }}
        />
      </div>
    ),
    { ...SIZE },
  );
}

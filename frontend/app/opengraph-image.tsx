import { ImageResponse } from "next/og";

export const alt = "Runlens — AI-powered running gait analysis";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#0F0F0F",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          fontFamily: "system-ui, sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Teal radial glow in top-right */}
        <div
          style={{
            position: "absolute",
            top: "-120px",
            right: "-120px",
            width: "500px",
            height: "500px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(0,200,150,0.15) 0%, rgba(0,200,150,0) 70%)",
          }}
        />

        {/* Teal accent bar */}
        <div
          style={{
            width: "56px",
            height: "4px",
            background: "#00C896",
            borderRadius: "2px",
            marginBottom: "36px",
          }}
        />

        {/* Brand */}
        <div
          style={{
            fontSize: "68px",
            fontWeight: "800",
            color: "#ffffff",
            letterSpacing: "-2px",
            lineHeight: 1,
            marginBottom: "20px",
          }}
        >
          Runlens.io
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: "30px",
            color: "#9ca3af",
            fontWeight: "400",
            marginBottom: "12px",
          }}
        >
          AI-powered running gait analysis
        </div>

        {/* Sub-tagline */}
        <div
          style={{
            fontSize: "22px",
            color: "#4b5563",
          }}
        >
          Upload a video · Get instant form feedback
        </div>

        {/* Bottom teal bar */}
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

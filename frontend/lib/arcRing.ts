// Shared math for the 270°-sweep progress ring used by MetricCards' ArcRing
// (plain SVG) and the share-card's HeroRing (Satori/ImageResponse). The two
// components render in different runtimes (DOM vs. Satori's restricted JSX
// subset) so their markup isn't shared, but the arc geometry and ring colors
// should stay identical.

export const RING_GOOD_COLOR = "#00C896";
export const RING_WARN_COLOR = "#F59E0B";
const SWEEP_FRACTION = 0.75;

export function computeArcGeometry(radius: number, score: number) {
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * SWEEP_FRACTION;
  const fillLength = arcLength * (Math.min(Math.max(score, 0), 100) / 100);
  return { circumference, arcLength, fillLength };
}

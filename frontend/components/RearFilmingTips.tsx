/** Expandable "How to film the rear view" guidance, shown wherever a rear
 * clip can be added (VideoUploader on the home page, AddRearVideoControl on
 * the results page). Collapsed by default so it costs one line of space.
 * Each tip maps to something the analysis is sensitive to — see
 * backend/rear_confidence.py capture_notes for the ones we can detect. */
const TIPS: { title: string; body: string }[] = [
  {
    title: "Use a treadmill if you can",
    body: "Running away from the camera makes you smaller with every stride. On a treadmill you stay the same size.",
  },
  {
    title: "Directly behind, 2–3 m back",
    body: "Line the camera up with the middle of your back, at about hip height, with your whole body and shoes in frame.",
  },
  {
    title: "Keep the phone level",
    body: "Prop it on something stable and use your camera's level or grid. A tilted frame skews left/right comparisons.",
  },
  {
    title: "Record at 60 fps, 1080p",
    body: "60 fps gives a sharper read of each stride; 1080p keeps a 15–20 s clip under the 100 MB limit.",
  },
  {
    title: "15–20 seconds of steady running",
    body: "Start filming once you're at your normal pace, not while speeding up.",
  },
  {
    title: "Fitted shorts, top tucked or short",
    body: "We need to see where your hips and knees are — loose clothing hides them.",
  },
];

export default function RearFilmingTips() {
  return (
    <details className="group rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-left">
      <summary className="cursor-pointer list-none text-xs font-medium text-gray-300 hover:text-white flex items-center gap-1.5">
        <span aria-hidden className="text-primary transition-transform group-open:rotate-90">▸</span>
        How to film the rear view
      </summary>
      <ul className="mt-2.5 space-y-2 pb-1">
        {TIPS.map((t) => (
          <li key={t.title}>
            <p className="text-xs font-semibold text-white">{t.title}</p>
            <p className="text-xs text-gray-400 leading-relaxed">{t.body}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

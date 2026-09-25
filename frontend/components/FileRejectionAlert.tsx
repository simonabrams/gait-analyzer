/** Inline alert under a video dropzone explaining why a file was refused
 * (see lib/videoValidation.ts's rejectionMessage). role="alert" so screen
 * readers announce it the moment it appears. */
export default function FileRejectionAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-lg border border-red-400/50 bg-red-400/10 px-3 py-2.5 text-sm text-red-300"
    >
      <span aria-hidden className="leading-5">⚠</span>
      <p className="leading-5">{message}</p>
    </div>
  );
}

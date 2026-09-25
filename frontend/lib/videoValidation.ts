/** Shared dropzone validation for anything that uploads a running video —
 * VideoUploader (the primary side-view upload) and AddRearVideoControl (the
 * optional rear-view upload). Kept in one place so the two never drift. */
import type { FileRejection } from "react-dropzone";

export const ALLOWED_VIDEO_TYPES = { "video/mp4": [".mp4"], "video/quicktime": [".mov"] };

// Sized for the 10-15s clip we recommend (see HomeClient/about-page copy),
// not the old 30-60s guidance — generous headroom over what that actually
// produces, not a hard technical ceiling.
export const MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024;

const MAX_MB = Math.round(MAX_VIDEO_SIZE_BYTES / (1024 * 1024));

/** User-facing reason a dropped/picked file was refused, or null if nothing
 * was. react-dropzone rejects silently (the file just never gets selected),
 * so without this the Analyze button stays disabled with no explanation —
 * most often for a 4K clip picked from the Files app, which skips the
 * re-encode iOS applies to Photos picks and easily exceeds the limit. */
export function rejectionMessage(rejections: FileRejection[]): string | null {
  const first = rejections[0];
  if (!first) return null;
  const codes = first.errors.map((e) => e.code);
  if (codes.includes("file-too-large")) {
    const mb = Math.round(first.file.size / (1024 * 1024));
    return (
      `“${first.file.name}” is ${mb} MB — the limit is ${MAX_MB} MB. ` +
      `Trim it to 10–20 seconds, or record at 1080p instead of 4K, and try again.`
    );
  }
  if (codes.includes("file-invalid-type")) {
    return `“${first.file.name}” isn't a supported video. Upload an MP4 or MOV file.`;
  }
  if (codes.includes("too-many-files")) {
    return "Choose one video at a time.";
  }
  return first.errors[0]?.message ?? "That file couldn't be used. Try another video.";
}

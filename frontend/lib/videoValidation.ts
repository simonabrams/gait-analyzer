/** Shared dropzone validation for anything that uploads a running video —
 * VideoUploader (the primary side-view upload) and AddRearVideoControl (the
 * optional rear-view upload). Kept in one place so the two never drift. */

export const ALLOWED_VIDEO_TYPES = { "video/mp4": [".mp4"], "video/quicktime": [".mov"] };

// Sized for the 10-15s clip we recommend (see HomeClient/about-page copy),
// not the old 30-60s guidance — generous headroom over what that actually
// produces, not a hard technical ceiling.
export const MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024;

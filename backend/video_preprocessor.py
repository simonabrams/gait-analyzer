"""
Video preprocessing: resize, re-encode (H.264/MP4), and trim to 3 minutes
(or to the analysis window, when the caller passes its frame cap). Reduces
OOM risk. If OOM persists at 720p, set VIDEO_MAX_HEIGHT=480 via env without
redeploying.
"""
import json
import logging
import os
import subprocess
from datetime import datetime

import cv2

logger = logging.getLogger(__name__)

RESOLUTION_PRESETS = {
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
}

MAX_DURATION_SEC = 180


def _get_target_height() -> int:
    try:
        return int(os.environ.get("VIDEO_MAX_HEIGHT", "720"))
    except ValueError:
        return 720


def get_video_creation_time(input_path: str) -> datetime | None:
    """Read creation_time from container metadata via ffprobe. Returns UTC datetime or None."""
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=creation_time",
                "-of",
                "csv=p=0",
                input_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if out.returncode != 0 or not out.stdout or not out.stdout.strip():
            return None
        raw = out.stdout.strip()
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if "+" in raw or raw.count("-") > 2:
            return datetime.fromisoformat(raw)
        return datetime.fromisoformat(raw + "+00:00")
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
        logger.debug("Could not get video creation_time for %s: %s", input_path, e)
        return None


def probe_source(input_path: str) -> dict:
    """What was actually uploaded: codec, frame rate and file size, straight
    from the container via ffprobe. Recorded so we can see what phones send
    (e.g. an iPhone 4K/60 HEVC clip arriving as 30 fps H.264 means the device
    re-encoded it before upload). Best effort: {} if ffprobe fails."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_name,avg_frame_rate,r_frame_rate:format=bit_rate",
                "-of", "json", input_path,
            ],
            capture_output=True, text=True, timeout=15, check=False,
        )
        info = json.loads(out.stdout or "{}")
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
        logger.debug("ffprobe failed for %s: %s", input_path, e)
        return {}
    stream = (info.get("streams") or [{}])[0]
    result = {"original_codec": stream.get("codec_name")}
    avg_fps = _parse_rate(stream.get("avg_frame_rate"))
    if avg_fps:
        result["original_fps"] = round(avg_fps, 2)
    bit_rate = (info.get("format") or {}).get("bit_rate")
    if bit_rate and str(bit_rate).isdigit():
        result["original_bitrate_mbps"] = round(int(bit_rate) / 1_000_000, 1)
    try:
        result["original_size_mb"] = round(os.path.getsize(input_path) / (1024 * 1024), 1)
    except OSError:
        pass
    return result


def _parse_rate(rate: str | None) -> float | None:
    """ffprobe's "60000/1001" -> 59.94; None for missing or "0/0"."""
    try:
        num, _, den = (rate or "").partition("/")
        value = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return None
    return value if value > 0 else None


def analysis_window_sec(fps: float, max_frames: int | None, target_fps: float | None) -> float | None:
    """How many seconds of video the analysis will actually read: the runners
    keep every frame_skip-th frame and stop at max_frames (job_runner /
    rear_job_runner). Preprocessing past that point is wasted work — a 41 s
    4K rear clip spent ~90 s here for 30 s of analysed video. +1 s margin so
    rounding never starves the last frames. None = no cap."""
    if not max_frames or max_frames <= 0 or not fps or fps <= 0:
        return None
    frame_skip = max(1, round(fps / target_fps)) if target_fps and target_fps > 0 else 1
    return max_frames * frame_skip / fps + 1.0


def preprocess_video(
    input_path: str,
    output_path: str,
    target_height: int | None = None,
    max_frames: int | None = None,
    target_fps: float | None = None,
) -> dict:
    """Downscale to target_height, re-encode to H.264 and trim. Trims to 3
    minutes (was_trimmed, which the UI warns about) and, when max_frames is
    given, to just the seconds the analysis will read (analysis_window_sec,
    silent: the runners would ignore those frames anyway)."""
    if target_height is None:
        target_height = _get_target_height()

    creation_time = get_video_creation_time(input_path)
    source = probe_source(input_path)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {input_path}")
    # OpenCV applies the container's rotation, so these are display dimensions
    # (a portrait iPhone clip reads as 2160x3840) — kept from before the
    # ffmpeg switch so output sizes don't change.
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    orig_duration_sec = total_frames / fps if fps > 0 else 0

    orig_res = f"{orig_w}x{orig_h}"
    was_trimmed = orig_duration_sec > MAX_DURATION_SEC
    output_duration_sec = min(orig_duration_sec, MAX_DURATION_SEC)
    if was_trimmed:
        logger.warning(
            "Video longer than 3 minutes (%.1fs); trimming to first 3 minutes",
            orig_duration_sec,
        )
    window = analysis_window_sec(fps, max_frames, target_fps)
    if window is not None:
        output_duration_sec = min(output_duration_sec, window)

    if orig_h <= target_height:
        out_w, out_h = orig_w, orig_h
        was_resized = False
    else:
        new_w = round(orig_w * target_height / orig_h)
        out_w = (new_w // 2) * 2
        out_h = target_height
        was_resized = True
    out_res = f"{out_w}x{out_h}"

    try:
        _transcode_ffmpeg(input_path, output_path, out_w, out_h, fps, output_duration_sec)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        stderr = getattr(e, "stderr", b"") or b""
        logger.warning(
            "ffmpeg preprocessing failed (%s); falling back to OpenCV. %s",
            e, stderr[-500:].decode(errors="replace"),
        )
        _transcode_opencv(input_path, output_path, out_w, out_h, fps, output_duration_sec, was_resized)

    output_size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 1)

    result = {
        "original_resolution": orig_res,
        "output_resolution": out_res,
        "original_duration_sec": round(orig_duration_sec, 1),
        "output_duration_sec": round(output_duration_sec, 1),
        "was_resized": was_resized,
        "was_trimmed": was_trimmed,
        "output_size_mb": output_size_mb,
        **source,
    }
    if creation_time is not None:
        result["creation_time_iso"] = creation_time.isoformat()
    return result


def _transcode_ffmpeg(input_path, output_path, out_w, out_h, fps, duration_sec):
    """One ffmpeg pass: decode, scale, trim, H.264 at a fast preset. Constant
    frame rate at the source's nominal fps, matching what the OpenCV writer
    produced before (downstream frame_skip / effective_fps math assumes it)."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", input_path,
            "-t", f"{duration_sec:.3f}",
            "-vf", f"scale={out_w}:{out_h}:flags=area",
            "-r", f"{fps:.6f}", "-fps_mode", "cfr",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


def _transcode_opencv(input_path, output_path, out_w, out_h, fps, duration_sec, was_resized):
    """The original frame-by-frame path, kept as a fallback if ffmpeg fails."""
    cap = cv2.VideoCapture(input_path)
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc("m", "p", "4", "v"), fps, (out_w, out_h))
    max_frames_to_write = int(round(duration_sec * fps))
    try:
        written = 0
        while written < max_frames_to_write:
            ret, frame = cap.read()
            if not ret:
                break
            if was_resized:
                frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
            writer.write(frame)
            written += 1
    finally:
        cap.release()
        writer.release()


def upload_summary(meta: dict | None) -> dict:
    """The preprocess_video() fields worth a glance in the pipeline_timing log
    line (backend/step_timer.py): what the device sent vs. what we analysed."""
    meta = meta or {}
    keys = {
        "original_resolution": "original_resolution",
        "original_codec": "original_codec",
        "original_fps": "original_fps",
        "original_size_mb": "original_size_mb",
        "original_duration_sec": "clip_sec",
        "output_duration_sec": "analysed_sec",
    }
    return {label: meta[key] for key, label in keys.items() if meta.get(key) is not None}

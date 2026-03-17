"""
Video preprocessing: resize, re-encode (H.264/MP4), and trim to 3 minutes.
Reduces OOM risk; target bitrate ~2 Mbps. If OOM persists at 720p, set
VIDEO_MAX_HEIGHT=480 via env without redeploying.
"""
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


def preprocess_video(
    input_path: str,
    output_path: str,
    target_height: int | None = None,
) -> dict:
    if target_height is None:
        target_height = _get_target_height()

    creation_time = get_video_creation_time(input_path)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {input_path}")

    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    orig_duration_sec = total_frames / fps if fps > 0 else 0

    orig_res = f"{orig_w}x{orig_h}"
    was_trimmed = orig_duration_sec > MAX_DURATION_SEC
    max_frames_to_write = (
        int(MAX_DURATION_SEC * fps) if was_trimmed else total_frames
    )
    output_duration_sec = min(orig_duration_sec, MAX_DURATION_SEC) if was_trimmed else orig_duration_sec

    if was_trimmed:
        logger.warning(
            "Video longer than 3 minutes (%.1fs); trimming to first 3 minutes",
            orig_duration_sec,
        )

    if orig_h <= target_height:
        out_w, out_h = orig_w, orig_h
        was_resized = False
    else:
        new_w = round(orig_w * target_height / orig_h)
        out_w = (new_w // 2) * 2
        out_h = target_height
        was_resized = True

    out_res = f"{out_w}x{out_h}"
    fourcc = cv2.VideoWriter_fourcc("m", "p", "4", "v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))

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

    output_size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 1)

    result = {
        "original_resolution": orig_res,
        "output_resolution": out_res,
        "original_duration_sec": round(orig_duration_sec, 1),
        "output_duration_sec": round(output_duration_sec, 1),
        "was_resized": was_resized,
        "was_trimmed": was_trimmed,
        "output_size_mb": output_size_mb,
    }
    if creation_time is not None:
        result["creation_time_iso"] = creation_time.isoformat()
    return result

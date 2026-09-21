"""
Runs the rear-view analysis: decode -> MediaPipe Pose -> rear_metrics. The rear
counterpart of job_runner.run_analysis, but much smaller: JSON only (no
annotated video, no dashboard PNG), so there is no frame cache and no ffmpeg.

The frame-reading loop below intentionally mirrors run_analysis's rather than
sharing it: run_analysis's fps / frame_skip handling has bitten before (see the
comment on `effective_fps` there) and the side path shouldn't be refactored
without real-video verification. Folding both loops into one helper is a good
follow-up once that can be tested end to end. The pieces that don't carry that
risk (CHUNK_SIZE, _resize_and_letterbox) are imported, not copied.
"""

from pathlib import Path

import cv2

from backend.job_runner import CHUNK_SIZE, _resize_and_letterbox
from backend.pose_extractor import extract_poses
from backend.rear_metrics import compute_rear_metrics


def run_rear_analysis(video_path, max_frames=None, max_width=None, target_fps=None):
    """Returns {"rear_view": dict, "frames_used": int, "truncated": bool}.

    Raises RuntimeError if the video can't be opened or has no frames — the
    caller marks only the rear video failed; the side result is unaffected.
    """
    video_path = Path(video_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_skip = max(1, round(fps / target_fps)) if target_fps and target_fps > 0 else 1
        # Rate the kept frames actually arrive at — every time-based constant
        # downstream (stride limits, smoothing window) is in units of kept
        # frames per second, exactly as in run_analysis.
        effective_fps = fps / frame_skip

        pose_frames = []
        frames_used = 0
        truncated = False
        while True:
            chunk, chunk_timestamps = [], []
            for _ in range(CHUNK_SIZE):
                if max_frames and max_frames > 0 and frames_used >= max_frames:
                    truncated = True
                    break
                exhausted = False
                for _ in range(frame_skip - 1):
                    if not cap.read()[0]:
                        exhausted = True
                        break
                if exhausted:
                    break
                ts_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                ret, frame = cap.read()
                if not ret:
                    break
                chunk.append(_resize_and_letterbox(frame, max_width))
                chunk_timestamps.append(ts_ms)
                frames_used += 1
            if not chunk:
                break
            start_idx = frames_used - len(chunk)
            pose_frames.extend(
                extract_poses(chunk, start_frame_idx=start_idx, timestamps_ms=chunk_timestamps)
            )
            del chunk
    finally:
        cap.release()

    if not pose_frames:
        raise RuntimeError("No frames read from video")

    rear_view = compute_rear_metrics(pose_frames, effective_fps, video_file=video_path.name)
    return {"rear_view": rear_view, "frames_used": frames_used, "truncated": truncated}

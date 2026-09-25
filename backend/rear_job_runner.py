"""
Runs the rear-view analysis: decode -> MediaPipe Pose -> rear_metrics -> annotated
(skeleton-overlay) video. The rear counterpart of job_runner.run_analysis, smaller
in one respect (no dashboard PNG, no numeric metrics panel on the video — see
visualizer.annotate_rear_frame) but otherwise mirrors its frame-caching + two-pass
structure so the annotated video can be built without decoding the source twice.

The frame-reading loop below intentionally mirrors run_analysis's rather than
sharing it: run_analysis's fps / frame_skip handling has bitten before (see the
comment on `effective_fps` there) and the side path shouldn't be refactored
without real-video verification. Folding both loops into one helper is a good
follow-up once that can be tested end to end. The pieces that don't carry that
risk (CHUNK_SIZE, _resize_and_letterbox, _sanitize_fps_for_writer) are imported,
not copied.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from backend.job_runner import CHUNK_SIZE, _resize_and_letterbox, _sanitize_fps_for_writer
from backend.pose_extractor import extract_poses
from backend.rear_metrics import compute_rear_metrics
from backend.step_timer import StepTimer
from backend.visualizer import annotate_rear_frame


def run_rear_analysis(video_path, max_frames=None, max_width=None, target_fps=None, timer=None):
    """Returns {"rear_view": dict, "annotated_video_path": str, "temp_paths": list[str],
    "frames_used": int, "truncated": bool}.

    Raises RuntimeError if the video can't be opened or has no frames — the
    caller marks only the rear video failed; the side result is unaffected.
    Caller is responsible for unlinking temp_paths (mirrors run_analysis).
    """
    video_path = Path(video_path)
    temp_paths = []
    timer = timer or StepTimer()
    try:
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
            out_h = out_w = None
            # Same reasoning as run_analysis: cache each processed frame as JPEG
            # bytes so the annotation pass can replay them without a second full
            # video decode, bounding memory for long/large rear clips too.
            frame_cache: list[bytes] = []
            _JPEG_PARAMS = [int(cv2.IMWRITE_JPEG_QUALITY), 92]

            while True:
                chunk, chunk_timestamps = [], []
                with timer.step("decode"):
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
                        frame = _resize_and_letterbox(frame, max_width)
                        if out_w is None:
                            out_h, out_w = frame.shape[0], frame.shape[1]
                        _, enc = cv2.imencode(".jpg", frame, _JPEG_PARAMS)
                        frame_cache.append(bytes(enc))
                        chunk.append(frame)
                        chunk_timestamps.append(ts_ms)
                        frames_used += 1
                if not chunk:
                    break
                start_idx = frames_used - len(chunk)
                with timer.step("pose"):
                    pose_frames.extend(
                        extract_poses(chunk, start_frame_idx=start_idx, timestamps_ms=chunk_timestamps)
                    )
                del chunk
        finally:
            cap.release()

        timer.info.update(
            source_fps=float(fps),
            effective_fps=float(effective_fps),
            frames_used=frames_used,
            truncated=truncated,
        )
        if not pose_frames:
            raise RuntimeError("No frames read from video")

        with timer.step("metrics"):
            rear_view = compute_rear_metrics(pose_frames, effective_fps, video_file=video_path.name)
        view = rear_view["meta"].get("view_check") or {}
        timer.info.update(view=view.get("view"), shoulder_ratio=view.get("shoulder_ratio"))

        pose_by_idx = {p["frame_idx"]: p for p in pose_frames}
        fd_v, annotated_video_path = tempfile.mkstemp(suffix=".mp4", prefix="gait_rear_annotated_")
        os.close(fd_v)
        temp_paths.append(annotated_video_path)
        out_fps = _sanitize_fps_for_writer(effective_fps)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        with timer.step("annotate"):
            writer = cv2.VideoWriter(annotated_video_path, fourcc, out_fps, (out_w, out_h))
            for i, jpeg_bytes in enumerate(frame_cache):
                frame = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                img = annotate_rear_frame(frame, i, pose_by_idx)
                if img is not None:
                    writer.write(img)
            frame_cache.clear()
            writer.release()

        fd_h264, h264_path = tempfile.mkstemp(suffix=".mp4", prefix="gait_rear_annotated_h264_")
        os.close(fd_h264)
        temp_paths.append(h264_path)
        with timer.step("encode"):
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", annotated_video_path,
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    h264_path,
                ],
                check=True,
                capture_output=True,
            )
        annotated_video_path = h264_path

        if truncated:
            rear_view["meta"]["truncated_frames"] = max_frames
            rear_view["meta"]["frames_used"] = frames_used

        return {
            "rear_view": rear_view,
            "annotated_video_path": annotated_video_path,
            "temp_paths": temp_paths,
            "frames_used": frames_used,
            "truncated": truncated,
        }
    except Exception:
        for p in temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass
        raise

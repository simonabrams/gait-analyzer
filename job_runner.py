"""
Runs the full gait analysis pipeline: pose extraction → metrics → heuristics
→ visualizer → dashboard → reporter. Uses tempfile for all outputs; caller
is responsible for cleanup.
"""

import json
import os
import tempfile
from pathlib import Path

import cv2
import matplotlib.pyplot as plt

from dashboard import create_dashboard
from heuristics import evaluate_heuristics
from metrics import compute_metrics
from pose_extractor import extract_poses
from reporter import generate_report
from visualizer import annotate_single_frame, build_frame_to_stride_flags


def _sanitize_fps_for_writer(fps):
    if fps is None or not (0 < fps < 1e6):
        return 30.0
    if fps > 120:
        return 120.0
    if fps < 1:
        return 30.0
    return fps


CHUNK_SIZE = 80


def _letterbox_to_square(frame):
    """Pad frame to square so MediaPipe pose (NORM_RECT path) works without IMAGE_DIMENSIONS warning."""
    h, w = frame.shape[:2]
    if w == h:
        return frame
    size = max(w, h)
    pad_w = (size - w) // 2
    pad_h = (size - h) // 2
    return cv2.copyMakeBorder(
        frame, pad_h, size - h - pad_h, pad_w, size - w - pad_w,
        cv2.BORDER_CONSTANT, value=(0, 0, 0),
    )


def _resize_and_letterbox(frame, max_width):
    """Resize by max_width (aspect preserved) then letterbox to square."""
    if max_width and max_width > 0 and frame.shape[1] > max_width:
        r = max_width / frame.shape[1]
        new_w = max_width
        new_h = int(frame.shape[0] * r)
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return _letterbox_to_square(frame)


def run_analysis(
    video_path,
    height_cm,
    progress_callback=None,
    max_frames=None,
    max_width=None,
):
    """
    Run the full pipeline and return paths to outputs. All outputs are
    written to temp files (delete=False); caller should remove them when done.

    Args:
        video_path: Path to MP4 or MOV.
        height_cm: Runner height in cm.
        progress_callback: Optional callable(percent: float, message: str).
        max_frames: If set, stop reading after this many frames (saves memory).
        max_width: If set, resize each frame to this width (aspect preserved).

    Returns:
        Dict with: results, annotated_video_path, dashboard_path, report_path,
        results_path, temp_paths, truncated (bool), frames_used (int).
    """
    video_path = Path(video_path)
    temp_paths = []
    truncated = False
    frames_used = 0

    def report(percent, message):
        if progress_callback:
            progress_callback(percent, message)

    try:
        report(0, "Opening video...")
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        pose_frames = []
        frames_used = 0
        out_h = out_w = None

        report(10, "Extracting poses...")
        while True:
            chunk = []
            for _ in range(CHUNK_SIZE):
                if max_frames and max_frames > 0 and frames_used >= max_frames:
                    truncated = True
                    break
                ret, frame = cap.read()
                if not ret:
                    break
                frame = _resize_and_letterbox(frame, max_width)
                if out_w is None:
                    out_h, out_w = frame.shape[0], frame.shape[1]
                chunk.append(frame)
                frames_used += 1
            if not chunk:
                break
            start_idx = frames_used - len(chunk)
            part = extract_poses(chunk, start_frame_idx=start_idx)
            pose_frames.extend(part)
            del chunk

        cap.release()
        if not pose_frames:
            raise RuntimeError("No frames read from video")

        report(40, "Computing metrics...")
        results = compute_metrics(
            pose_frames, height_cm, fps, video_file=video_path.name
        )
        results["flags"] = evaluate_heuristics(results)
        results_from_json = results

        report(50, "Generating annotated video...")
        pose_by_idx = {p["frame_idx"]: p for p in pose_frames}
        frame_flags = build_frame_to_stride_flags(
            results_from_json.get("strides", []),
            results_from_json.get("flags", []),
        )
        fd_v, annotated_video_path = tempfile.mkstemp(
            suffix=".mp4", prefix="gait_annotated_"
        )
        os.close(fd_v)
        temp_paths.append(annotated_video_path)
        out_fps = _sanitize_fps_for_writer(fps)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            annotated_video_path, fourcc, out_fps, (out_w, out_h)
        )
        cap2 = cv2.VideoCapture(str(video_path))
        for i in range(frames_used):
            ret, frame = cap2.read()
            if not ret:
                break
            frame = _resize_and_letterbox(frame, max_width)
            img = annotate_single_frame(
                frame, i, pose_by_idx, results_from_json, frame_flags
            )
            if img is not None:
                writer.write(img)
        cap2.release()
        writer.release()

        report(70, "Building dashboard...")
        fig = create_dashboard(results_from_json)
        fd_d, dashboard_path = tempfile.mkstemp(
            suffix=".png", prefix="gait_dashboard_"
        )
        os.close(fd_d)
        temp_paths.append(dashboard_path)
        fig.savefig(dashboard_path, dpi=150)
        plt.close(fig)

        report(90, "Writing report...")
        report_text = generate_report(results_from_json)
        fd_r, report_path = tempfile.mkstemp(
            suffix=".txt", prefix="gait_report_"
        )
        os.close(fd_r)
        temp_paths.append(report_path)
        with open(report_path, "w") as f:
            f.write(report_text)

        fd_j, results_path = tempfile.mkstemp(
            suffix=".json", prefix="gait_results_"
        )
        os.close(fd_j)
        temp_paths.append(results_path)
        with open(results_path, "w") as f:
            json.dump(results_from_json, f, indent=2)

        if truncated and results_from_json.get("meta"):
            results_from_json["meta"]["truncated_frames"] = max_frames
            results_from_json["meta"]["frames_used"] = frames_used

        report(100, "Done.")
        return {
            "results": results_from_json,
            "annotated_video_path": annotated_video_path,
            "dashboard_path": dashboard_path,
            "report_path": report_path,
            "results_path": results_path,
            "temp_paths": temp_paths,
            "truncated": truncated,
            "frames_used": frames_used,
        }
    except Exception:
        for p in temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass
        raise

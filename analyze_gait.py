"""
CLI entry point for gait analysis. Handles all file I/O: reads video, writes
results.json, annotated video, dashboard PNG, and text report. Orchestrates
pose_extractor, metrics, heuristics, visualizer, dashboard, and reporter.
For a web app, replace this with FastAPI/Streamlit endpoints that call the
same modules with parameters from the request/session.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt

from dashboard import create_dashboard
from heuristics import evaluate_heuristics
from metrics import compute_metrics
from pose_extractor import extract_poses
from reporter import generate_report
from visualizer import generate_annotated_frames


def _sanitize_fps_for_writer(fps):
    """Clamp FPS so VideoWriter + mp4v codec accept it (MPEG4 timebase denom <= 65535)."""
    if fps is None or not (fps > 0 and fps < 1e6):
        return 30.0
    if fps > 120:
        return 120.0
    if fps < 1:
        return 30.0
    return fps


def main():
    parser = argparse.ArgumentParser(description="Analyze running gait from a side-view video.")
    parser.add_argument("--video", required=True, help="Path to MP4 or MOV video file")
    parser.add_argument("--height", type=float, required=True, help="Runner height in cm (for scale)")
    parser.add_argument("--output-dir", default=None, help="Directory for outputs (default: same as video)")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)
    output_dir = Path(args.output_dir) if args.output_dir else video_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error: could not open video {video_path}", file=sys.stderr)
        sys.exit(1)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    if not frames:
        print("Error: no frames read from video", file=sys.stderr)
        sys.exit(1)

    pose_frames = extract_poses(frames)
    results = compute_metrics(pose_frames, args.height, fps, video_file=video_path.name)
    results["flags"] = evaluate_heuristics(results)

    results_path = output_dir / "results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {results_path}")

    with open(results_path) as f:
        results_from_json = json.load(f)

    annotated = generate_annotated_frames(frames, pose_frames, results_from_json)
    out_video_path = output_dir / f"{video_path.stem}_annotated.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    h, w = frames[0].shape[:2]
    # Use sanitized FPS for writing: MPEG4 rejects extreme timebases (denom > 65535)
    out_fps = _sanitize_fps_for_writer(fps)
    writer = cv2.VideoWriter(str(out_video_path), fourcc, out_fps, (w, h))
    for frame in annotated:
        writer.write(frame)
    writer.release()
    print(f"Saved {out_video_path}")

    fig = create_dashboard(results_from_json)
    dashboard_path = output_dir / f"{video_path.stem}_dashboard.png"
    fig.savefig(dashboard_path, dpi=150)
    plt.close(fig)
    print(f"Saved {dashboard_path}")

    report_text = generate_report(results_from_json)
    report_path = output_dir / f"{video_path.stem}_report.txt"
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"Saved {report_path}")
    print()
    print(report_text)


if __name__ == "__main__":
    main()

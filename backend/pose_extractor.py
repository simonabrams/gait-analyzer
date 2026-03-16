"""
Extract 33 body landmarks per frame from video using MediaPipe Pose (Tasks API).
Returns a list of per-frame landmark data; no file I/O for frames. Model is
downloaded to a cache dir on first use. In a web context, call with frames
from an upload or stream.
"""

import os
from pathlib import Path

# MediaPipe Pose landmark indices (BlazePose 33-point)
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

# Pose landmarker model: lite variant, good speed/accuracy for gait
_POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)


def _model_cache_path():
    d = Path(os.environ.get("GAIT_ANALYZER_CACHE", Path(__file__).resolve().parent / ".pose_model"))
    d.mkdir(parents=True, exist_ok=True)
    return d / "pose_landmarker_lite.task"


def _ensure_model():
    path = _model_cache_path()
    if path.exists():
        return str(path)
    try:
        import urllib.request
        urllib.request.urlretrieve(_POSE_MODEL_URL, path)
    except Exception as e:
        raise RuntimeError(
            f"Could not download pose model from {_POSE_MODEL_URL}. "
            f"Download it manually and set GAIT_ANALYZER_CACHE to a dir containing pose_landmarker_lite.task. Error: {e}"
        ) from e
    return str(path)


def extract_poses(frames, model_complexity=1, start_frame_idx=0, timestamps_ms=None):
    """
    Run MediaPipe Pose on each frame and return landmark data (Tasks API).

    Args:
        frames: List of BGR images (numpy arrays, HxWx3).
        model_complexity: Ignored; kept for API compatibility. Tasks API uses bundled model.
        start_frame_idx: Base index for frame_idx in output (for chunked processing).
        timestamps_ms: Optional list of actual frame timestamps in milliseconds (from
            cap.get(cv2.CAP_PROP_POS_MSEC)). If provided, used instead of assuming
            constant FPS. Must match len(frames).

    Returns:
        List of dicts, one per frame: {"frame_idx": int, "timestamp_ms": float,
        "landmarks": list of {"x": float, "y": float, "z": float, "visibility": float}}
        in normalized coords [0,1]. Frames where no pose is detected have "landmarks": None.
    """
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python.core import base_options
    from mediapipe.tasks.python.vision import pose_landmarker
    from mediapipe.tasks.python.vision.core import vision_task_running_mode

    model_path = _ensure_model()
    base_opts = base_options.BaseOptions(model_asset_path=model_path)
    opts = pose_landmarker.PoseLandmarkerOptions(
        base_options=base_opts,
        running_mode=vision_task_running_mode.VisionTaskRunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = pose_landmarker.PoseLandmarker.create_from_options(opts)

    out = []
    last_ts_int = -1
    for i, frame in enumerate(frames):
        idx = start_frame_idx + i
        ts_ms = float(timestamps_ms[i]) if timestamps_ms is not None and i < len(timestamps_ms) else float(i * 33)
        # MediaPipe requires strictly monotonically increasing integer timestamps.
        # cap.get(CAP_PROP_POS_MSEC) can return equal values on VFR video after truncation.
        ts_int = max(last_ts_int + 1, int(ts_ms))
        last_ts_int = ts_int
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(mp_img, ts_int)
        if not result.pose_landmarks:
            out.append({"frame_idx": idx, "timestamp_ms": ts_int, "landmarks": None})
            continue
        pose_lms = result.pose_landmarks[0]
        landmarks = [
            {
                "x": getattr(lm, "x", 0.0) or 0.0,
                "y": getattr(lm, "y", 0.0) or 0.0,
                "z": getattr(lm, "z", 0.0) or 0.0,
                "visibility": getattr(lm, "visibility", 0.0) or 0.0,
            }
            for lm in pose_lms
        ]
        out.append({"frame_idx": idx, "timestamp_ms": ts_int, "landmarks": landmarks})
    landmarker.close()
    return out

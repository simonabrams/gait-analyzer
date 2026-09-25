"""Tests for backend.video_preprocessor. The ffmpeg round trip is skipped when
ffmpeg isn't installed (the worker image always has it)."""
import shutil
import subprocess

import cv2
import pytest

from backend import video_preprocessor as vp


def test_analysis_window_matches_what_the_runners_read():
    # 60 fps source, target 30 -> every 2nd frame kept; 900 kept frames = 30 s.
    assert vp.analysis_window_sec(60.0, 900, 30.0) == pytest.approx(31.0)
    # Target above the source rate keeps every frame: 900 frames at 30 fps = 30 s.
    assert vp.analysis_window_sec(30.0, 900, 60.0) == pytest.approx(31.0)
    assert vp.analysis_window_sec(59.94, 300, 60.0) == pytest.approx(300 / 59.94 + 1)
    # No frame cap -> no window.
    assert vp.analysis_window_sec(60.0, None, 30.0) is None
    assert vp.analysis_window_sec(60.0, 0, 30.0) is None


def test_parse_rate():
    assert vp._parse_rate("60000/1001") == pytest.approx(59.94, abs=0.01)
    assert vp._parse_rate("30/1") == 30.0
    assert vp._parse_rate("0/0") is None
    assert vp._parse_rate(None) is None


def test_upload_summary_picks_log_fields_and_skips_missing():
    meta = {"original_resolution": "2160x3840", "original_fps": 30.0, "original_duration_sec": 41.0,
            "output_duration_sec": 31.0, "output_size_mb": 4.0}
    assert vp.upload_summary(meta) == {
        "original_resolution": "2160x3840", "original_fps": 30.0, "clip_sec": 41.0, "analysed_sec": 31.0,
    }
    assert vp.upload_summary(None) == {}


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_ffmpeg_path_resizes_trims_and_keeps_orientation_and_fps(tmp_path):
    src, out = tmp_path / "src.mp4", tmp_path / "out.mp4"
    # 4 s of 60 fps portrait video (stored landscape + rotation, like an iPhone clip).
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=60", "-t", "4",
         "-c:v", "libx264", "-preset", "ultrafast", str(tmp_path / "land.mp4")],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-display_rotation", "90", "-i", str(tmp_path / "land.mp4"),
         "-c", "copy", str(src)],
        check=True,
    )
    meta = vp.preprocess_video(str(src), str(out), target_height=640, max_frames=60, target_fps=30.0)

    cap = cv2.VideoCapture(str(out))
    w, h, fps, frames = cap.get(3), cap.get(4), cap.get(5), cap.get(7)
    cap.release()
    assert (w, h) == (360, 640)  # portrait kept, height capped
    assert fps == pytest.approx(60.0)
    # 60 kept frames at every-2nd-frame = 2 s, +1 s margin -> ~3 s of the 4 s clip.
    assert frames == pytest.approx(180, abs=2)
    assert meta["was_trimmed"] is False  # only the 3-minute trim warns the user
    assert meta["original_codec"] == "h264" and meta["original_fps"] == pytest.approx(60.0)
    assert meta["output_duration_sec"] == pytest.approx(3.0)

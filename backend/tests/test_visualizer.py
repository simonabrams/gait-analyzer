"""Unit tests for backend.visualizer — the skeleton-drawing primitives shared by
the side and rear annotators. This module had no test coverage before the
rear-view annotation work (backend/rear_job_runner.py); these focus on the
extracted/new pieces (draw_skeleton, annotate_rear_frame) and a light
regression check that annotate_single_frame's refactor didn't change its output."""
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from backend.visualizer import annotate_rear_frame, annotate_single_frame, draw_skeleton  # noqa: E402

_GREEN = (0, 255, 0)
_RED = (0, 0, 255)


def _blank(w=100, h=100):
    return np.zeros((h, w, 3), dtype=np.uint8)


def _landmarks(n=33, x=0.5, y=0.5):
    """n landmarks all at the same normalised point (a specific pixel to probe)."""
    return [{"x": x, "y": y, "z": 0.0, "visibility": 1.0} for _ in range(n)]


def _pose_by_idx(frame_idx, landmarks):
    return {frame_idx: {"frame_idx": frame_idx, "landmarks": landmarks}}


# ---- draw_skeleton -----------------------------------------------------------------
def test_draw_skeleton_draws_something_when_landmarks_present():
    img = _blank()
    draw_skeleton(img, _landmarks())
    assert img.any()  # no longer all-black


def test_draw_skeleton_mutates_in_place_and_returns_none():
    img = _blank()
    assert draw_skeleton(img, _landmarks()) is None
    assert img.any()


def test_draw_skeleton_unhighlighted_joint_is_green():
    img = _blank(200, 200)
    lm = _landmarks(x=0.5, y=0.5)
    draw_skeleton(img, lm)
    assert tuple(img[100, 100]) == _GREEN


def test_draw_skeleton_highlighted_joint_is_red_not_green():
    # A single landmark: with all 33 at the same point, later (unhighlighted)
    # circles would just paint back over an earlier highlighted one.
    img_default = _blank(200, 200)
    img_highlighted = _blank(200, 200)
    lm = _landmarks(n=1, x=0.5, y=0.5)
    draw_skeleton(img_default, lm)
    draw_skeleton(img_highlighted, lm, highlighted_joints={0})
    assert tuple(img_default[100, 100]) == _GREEN
    assert tuple(img_highlighted[100, 100]) == _RED


def test_draw_skeleton_does_not_crash_on_short_landmark_list():
    """POSE_CONNECTIONS references indices up to 28; a shorter list (e.g. a
    partial detection) must be tolerated, not index-error."""
    img = _blank()
    draw_skeleton(img, _landmarks(n=5))  # no exception


def test_draw_skeleton_no_highlights_by_default():
    img_a = _blank()
    img_b = _blank()
    draw_skeleton(img_a, _landmarks())
    draw_skeleton(img_b, _landmarks(), highlighted_joints=None)
    assert np.array_equal(img_a, img_b)


# ---- annotate_rear_frame ------------------------------------------------------------
def test_annotate_rear_frame_returns_none_for_none_frame():
    assert annotate_rear_frame(None, 0, {}) is None


def test_annotate_rear_frame_returns_a_copy_not_the_original():
    frame = _blank()
    out = annotate_rear_frame(frame, 0, {})
    assert out is not frame


def test_annotate_rear_frame_unchanged_when_no_pose_for_this_frame():
    frame = _blank()
    out = annotate_rear_frame(frame, 0, {})  # empty pose_by_idx
    assert np.array_equal(out, frame)
    # A pose exists, but not for frame_idx=99 (only frame_idx=5 is present).
    out2 = annotate_rear_frame(frame, 99, _pose_by_idx(5, _landmarks()))
    assert np.array_equal(out2, frame)


def test_annotate_rear_frame_draws_skeleton_when_pose_present():
    frame = _blank(200, 200)
    out = annotate_rear_frame(frame, 0, _pose_by_idx(0, _landmarks(x=0.5, y=0.5)))
    assert out.any()
    assert tuple(out[100, 100]) == _GREEN


def test_annotate_rear_frame_unchanged_when_landmarks_are_none():
    frame = _blank()
    pose_by_idx = {0: {"frame_idx": 0, "landmarks": None}}
    out = annotate_rear_frame(frame, 0, pose_by_idx)
    assert np.array_equal(out, frame)


def test_annotate_rear_frame_never_draws_a_metrics_panel():
    """Deliberate difference from annotate_single_frame: rear frames should
    never have the semi-transparent numeric panel drawn in the top-left
    corner, since rear metrics are pattern indicators, not precise values."""
    frame = _blank(300, 300)
    out = annotate_rear_frame(frame, 0, _pose_by_idx(0, _landmarks(x=0.1, y=0.1)))
    # The metrics panel (if drawn) always starts at (10, 10) with a dark
    # semi-transparent fill; the far corner (280, 280) is well outside both
    # the panel and this test's single landmark, so it must stay untouched.
    assert tuple(out[280, 280]) == (0, 0, 0)


# ---- annotate_single_frame: refactor regression -----------------------------------
def _results(flags=None):
    return {"strides": [], "flags": flags or [], "summary": {}}


def test_annotate_single_frame_draws_skeleton_same_as_draw_skeleton_directly():
    frame = _blank(200, 200)
    pose_by_idx = _pose_by_idx(0, _landmarks(x=0.5, y=0.5))
    out = annotate_single_frame(frame, 0, pose_by_idx, _results(), suppress_metrics_panel=True)
    expected = _blank(200, 200)
    draw_skeleton(expected, _landmarks(x=0.5, y=0.5))
    assert np.array_equal(out, expected)


def test_annotate_single_frame_returns_none_for_none_frame():
    assert annotate_single_frame(None, 0, {}, _results()) is None


def test_annotate_single_frame_handles_no_pose_for_this_frame():
    frame = _blank()
    out = annotate_single_frame(frame, 0, {}, _results(), suppress_metrics_panel=True)
    assert np.array_equal(out, frame)

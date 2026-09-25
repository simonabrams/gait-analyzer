"""Tests for backend.view_check and the two places it gates results: a clip
uploaded to the wrong slot must say so instead of reporting confident but
meaningless numbers (the real case: a rear clip in the side slot read as
1 deg knee drive and 1 deg trunk lean, with coaching flags attached)."""
import json
import math
from pathlib import Path

import pytest

from backend import rear_metrics as rm
from backend.job_runner import apply_confidence_gate
from backend.tests.rear_fixtures import FPS, make_rear_frames
from backend.tests.test_job_runner import _results
from backend.view_check import classify_view

_SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "schema" / "results.schema.json").read_text())


def _lm(x, y, vis=1.0):
    return {"x": x, "y": y, "z": 0.0, "visibility": vis}


def _frames(camera_angle_deg, n=40, vis=1.0):
    """Torso seen with the camera `camera_angle_deg` away from straight
    behind (0 = rear view, 90 = side-on). Shoulders 0.16 wide, torso 0.20
    long, so the true frontal ratio is 0.8."""
    half_w = 0.08 * math.cos(math.radians(camera_angle_deg))
    hip_half_w = 0.05 * math.cos(math.radians(camera_angle_deg))
    frames = []
    for i in range(n):
        lm = [_lm(0.5, 0.5, vis) for _ in range(33)]
        lm[11], lm[12] = _lm(0.5 - half_w, 0.30, vis), _lm(0.5 + half_w, 0.30, vis)
        lm[23], lm[24] = _lm(0.5 - hip_half_w, 0.50, vis), _lm(0.5 + hip_half_w, 0.50, vis)
        frames.append({"frame_idx": i, "timestamp_ms": i * 33.3, "landmarks": lm})
    return frames


def test_rear_view_is_frontal():
    v = classify_view(_frames(0))
    assert v.view == "frontal" and abs(v.shoulder_ratio - 0.8) < 0.01


def test_side_view_is_side():
    assert classify_view(_frames(85)).view == "side"


def test_diagonal_camera_is_diagonal():
    assert classify_view(_frames(45)).view == "diagonal"


def test_too_few_usable_frames_is_unknown_not_a_guess():
    assert classify_view(_frames(0, n=5)).view == "unknown"
    assert classify_view(_frames(0, vis=0.2)).view == "unknown"
    assert classify_view([{"landmarks": None}] * 40).view == "unknown"


# ---- Side slot ------------------------------------------------------------
def test_frontal_clip_in_the_side_slot_hard_fails_even_when_metrics_look_plausible():
    gate, results = apply_confidence_gate(_results(), view=classify_view(_frames(0)))
    assert gate.hard_fail and gate.reason == "wrong_view"
    assert "rear-view slot" in gate.user_message
    assert results["summary"] == {} and results["flags"] == []
    assert results["meta"]["view_check"]["view"] == "frontal"


def test_side_and_diagonal_clips_pass_through_to_the_normal_gate():
    for angle in (85, 45):
        gate, results = apply_confidence_gate(_results(), view=classify_view(_frames(angle)))
        assert not gate.hard_fail
        assert results["meta"]["view_check"]["view"] in ("side", "diagonal")


# ---- Rear slot ------------------------------------------------------------
def test_side_clip_in_the_rear_slot_reports_wrong_view():
    frames = make_rear_frames()
    for p in frames:
        p["landmarks"][11] = _lm(0.49, 0.30)
        p["landmarks"][12] = _lm(0.51, 0.30)
    rv = rm.compute_rear_metrics(frames, FPS)
    assert rv["status"] == "insufficient_data"
    assert rv["confidence_gate"]["reason"] == "wrong_view"
    assert "from the side" in rv["confidence_gate"]["user_message"]
    assert rv["meta"]["view_check"]["view"] == "side"
    jsonschema = pytest.importorskip("jsonschema")
    doc = {"meta": {}, "summary": {}, "flags": [], "strides": [], "schema_version": 2, "rear_view": rv}
    jsonschema.Draft202012Validator(_SCHEMA).validate(doc)


def test_real_rear_clip_is_unaffected():
    rv = rm.compute_rear_metrics(make_rear_frames(), FPS)
    assert rv["status"] == "ok"
    assert rv["meta"]["view_check"]["view"] == "frontal"

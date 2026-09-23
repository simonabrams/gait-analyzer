"""Tests for backend.rear_worker.process_rear_video with download / preprocessing
/ pose extraction mocked out (SQLite in memory, same approach as
test_rear_video_api.py). The property that matters: whatever happens to the rear
video, the side run's row is left exactly as the side pipeline left it."""
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import rear_worker, worker
from backend.models import Base, Run, RunStatus, RunVideo, Subscription, SubscriptionTier

REAR_VIEW = {"status": "ok", "confidence_gate": {"reason": None}, "meta": {}}


@compiles(JSONB, "sqlite")
def _jsonb_as_json(type_, compiler, **kw):
    return "JSON"


@pytest.fixture
def env(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(rear_worker, "get_db_session", Session)
    monkeypatch.setattr(rear_worker, "download_file", MagicMock())
    monkeypatch.setattr(rear_worker, "preprocess_video", MagicMock(return_value={}))
    captured = MagicMock()
    monkeypatch.setattr(rear_worker, "posthog_capture", captured)

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    run_id = uuid.uuid4()
    with Session() as db:
        # A free user who has already used their scan: a refund here would be a bug.
        db.add(Subscription(user_id=user_id, tier=SubscriptionTier.free.value, referral_code="abc", free_scans_used=1))
        db.add(Run(id=run_id, user_id=user_id, height_cm=175, status=RunStatus.complete, progress_pct=100,
                   results_json={"summary": {"cadence_avg": 171}}))
        db.add(RunVideo(run_id=run_id, view_type="rear", r2_key=f"raw/{run_id}/rear.mp4", status="processing"))
        db.commit()
    return type("Env", (), {"Session": Session, "run_id": str(run_id), "user_id": user_id, "capture": captured})


def _side_snapshot(env):
    with env.Session() as db:
        run = db.get(Run, uuid.UUID(env.run_id))
        sub = db.query(Subscription).one()
        return run.status, run.progress_pct, run.results_json, run.error_message, sub.free_scans_used


def _rear(env):
    with env.Session() as db:
        return db.query(RunVideo).filter(RunVideo.view_type == "rear").one()


def test_success_stores_the_rear_view_and_marks_complete(env, monkeypatch):
    monkeypatch.setattr(rear_worker, "run_rear_analysis",
                        MagicMock(return_value={"rear_view": dict(REAR_VIEW, meta={}), "frames_used": 300, "truncated": False}))
    before = _side_snapshot(env)
    rear_worker.process_rear_video.run(env.run_id, f"raw/{env.run_id}/rear.mp4")
    row = _rear(env)
    assert row.status == "complete" and row.results_json["status"] == "ok" and row.error_message is None
    assert _side_snapshot(env) == before
    # Analytics carry status only — no gait values.
    env.capture.assert_called_once_with(env.user_id, "rear_run_completed", {"rear_status": "ok", "reason": None})


def test_insufficient_data_is_still_a_completed_task(env, monkeypatch):
    """The task ran fine; the *analysis* couldn't say anything. That's rear_view.status, not a task failure."""
    rv = {"status": "insufficient_data", "confidence_gate": {"reason": "insufficient_cycles"}, "meta": {}}
    monkeypatch.setattr(rear_worker, "run_rear_analysis",
                        MagicMock(return_value={"rear_view": rv, "frames_used": 40, "truncated": False}))
    rear_worker.process_rear_video.run(env.run_id, "k")
    row = _rear(env)
    assert row.status == "complete" and row.results_json["status"] == "insufficient_data"


def test_failure_fails_only_the_rear_video_and_never_touches_the_side_run_or_refunds(env, monkeypatch):
    monkeypatch.setattr(rear_worker, "run_rear_analysis", MagicMock(side_effect=RuntimeError("Could not open video")))
    before = _side_snapshot(env)
    with pytest.raises(RuntimeError):
        rear_worker.process_rear_video.run(env.run_id, "k")
    row = _rear(env)
    assert row.status == "failed" and "Could not open video" in row.error_message and row.results_json is None
    assert _side_snapshot(env) == before  # status, progress, results, error_message, free_scans_used all unchanged
    env.capture.assert_called_once_with(env.user_id, "rear_run_failed", {"error_type": "RuntimeError"})


def test_long_error_text_is_capped(env, monkeypatch):
    monkeypatch.setattr(rear_worker, "run_rear_analysis", MagicMock(side_effect=RuntimeError("x" * 5000)))
    with pytest.raises(RuntimeError):
        rear_worker.process_rear_video.run(env.run_id, "k")
    assert len(_rear(env).error_message) == rear_worker._ERROR_MESSAGE_MAX


def test_redelivered_task_for_a_finished_video_is_a_no_op(env, monkeypatch):
    analysis = MagicMock()
    monkeypatch.setattr(rear_worker, "run_rear_analysis", analysis)
    with env.Session() as db:
        row = db.query(RunVideo).one()
        row.status, row.results_json = "complete", REAR_VIEW
        db.commit()
    rear_worker.process_rear_video.run(env.run_id, "k")
    analysis.assert_not_called()
    rear_worker.download_file.assert_not_called()


def test_task_for_a_deleted_run_is_a_no_op(env, monkeypatch):
    analysis = MagicMock()
    monkeypatch.setattr(rear_worker, "run_rear_analysis", analysis)
    rear_worker.process_rear_video.run(str(uuid.uuid4()), "k")
    analysis.assert_not_called()


def test_current_rear_run_marker_is_cleared_after_success_and_failure(env, monkeypatch):
    monkeypatch.setattr(rear_worker, "run_rear_analysis",
                        MagicMock(return_value={"rear_view": dict(REAR_VIEW, meta={}), "frames_used": 1, "truncated": False}))
    rear_worker.process_rear_video.run(env.run_id, "k")
    assert worker._current_rear_run_id is None
    monkeypatch.setattr(rear_worker, "run_rear_analysis", MagicMock(side_effect=RuntimeError("x")))
    with env.Session() as db:
        db.query(RunVideo).one().status = "processing"
        db.commit()
    with pytest.raises(RuntimeError):
        rear_worker.process_rear_video.run(env.run_id, "k")
    assert worker._current_rear_run_id is None


def test_sigterm_marks_only_the_in_flight_rear_video_failed(env, monkeypatch):
    monkeypatch.setattr(worker, "get_db_session", env.Session)
    monkeypatch.setattr(worker, "_current_rear_run_id", env.run_id)
    before = _side_snapshot(env)
    with pytest.raises(SystemExit):
        worker._handle_sigterm(15, None)
    assert _rear(env).status == "failed"
    assert _side_snapshot(env) == before


def test_task_is_registered_on_its_own_queue_and_name():
    assert rear_worker.process_rear_video.name == "backend.rear_worker.process_rear_video"
    assert rear_worker.process_rear_video.queue == "rear_view"
    assert worker.app.conf.include == ["backend.rear_worker"]


# ---- _limits_from_env: rear fps override --------------------------------------------------
def test_gait_rear_target_fps_overrides_gait_target_fps(monkeypatch):
    monkeypatch.setenv("GAIT_TARGET_FPS", "15")
    monkeypatch.setenv("GAIT_REAR_TARGET_FPS", "30")
    assert rear_worker._limits_from_env() == (None, None, 30.0)


def test_falls_back_to_gait_target_fps_when_rear_override_unset(monkeypatch):
    monkeypatch.delenv("GAIT_REAR_TARGET_FPS", raising=False)
    monkeypatch.setenv("GAIT_TARGET_FPS", "15")
    assert rear_worker._limits_from_env() == (None, None, 15.0)


def test_max_frames_and_width_stay_shared_with_the_side_pipeline(monkeypatch):
    monkeypatch.setenv("GAIT_MAX_FRAMES", "900")
    monkeypatch.setenv("GAIT_MAX_WIDTH", "1280")
    monkeypatch.delenv("GAIT_TARGET_FPS", raising=False)
    monkeypatch.delenv("GAIT_REAR_TARGET_FPS", raising=False)
    assert rear_worker._limits_from_env() == (900, 1280, None)

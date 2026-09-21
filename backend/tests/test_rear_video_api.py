"""API-level tests for the optional rear-view video: the upload endpoint, the
read-time merge into `results`, and storage-first deletion including the rear key.

Runs through FastAPI's TestClient against in-memory SQLite (JSONB is compiled as
JSON below, and foreign keys are switched on so ON DELETE CASCADE is real), with
storage and Celery patched out — so it needs no Postgres, Redis or R2 and runs
in CI. It exercises endpoint/ORM logic only; the Alembic migration itself is NOT
executed here (it needs Postgres — see the note in 010_add_run_videos.py).
"""
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import consent, main
from backend.database import get_db
from backend.models import Base, ConsentRecord, Run, RunStatus, RunVideo

# A rear_view produced by the real module (checked-in sample).
SAMPLE = json.loads((Path(__file__).resolve().parent.parent / "schema" / "sample_run_both_views.json").read_text())
REAR_VIEW = SAMPLE["rear_view"]


@compiles(JSONB, "sqlite")
def _jsonb_as_json(type_, compiler, **kw):
    return "JSON"


MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
OWNER = f"anon:{uuid.uuid4()}"
STRANGER = f"anon:{uuid.uuid4()}"


@pytest.fixture
def env(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    def _get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = _get_db
    main.limiter.enabled = False

    uploads, deleted = [], []
    monkeypatch.setattr(main, "upload_file", lambda path, key: uploads.append(key))
    monkeypatch.setattr(main, "delete_object", lambda key: deleted.append(key))
    delay = MagicMock()
    monkeypatch.setattr("backend.rear_worker.process_rear_video.delay", delay)
    monkeypatch.setattr("backend.worker.process_video.delay", MagicMock())

    with Session() as db:
        for uid in (OWNER, STRANGER):
            db.add(ConsentRecord(user_id=uid, policy_version=consent.PRIVACY_POLICY_VERSION, age_confirmed=True))
        db.commit()

    yield SimpleNamespaceEnv(TestClient(main.app), Session, uploads, deleted, delay)
    main.app.dependency_overrides.clear()
    main.limiter.enabled = True


class SimpleNamespaceEnv:
    def __init__(self, client, Session, uploads, deleted, delay):
        self.client, self.Session, self.uploads, self.deleted, self.delay = client, Session, uploads, deleted, delay

    def make_run(self, user=OWNER, status=RunStatus.complete, results=None):
        run_id = uuid.uuid4()
        with self.Session() as db:
            db.add(Run(
                id=run_id, user_id=user, height_cm=175, status=status,
                raw_video_r2_key=f"raw/{run_id}/input.mp4",
                annotated_video_r2_key=f"processed/{run_id}/annotated.mp4",
                results_json=results,
            ))
            db.add(RunVideo(run_id=run_id, view_type="side", r2_key=f"raw/{run_id}/input.mp4"))
            db.commit()
        return run_id

    def rear_rows(self, run_id):
        with self.Session() as db:
            return db.query(RunVideo).filter(RunVideo.run_id == run_id, RunVideo.view_type == "rear").all()

    def post_rear(self, run_id, user=OWNER, content=MP4, name="rear.mp4"):
        return self.client.post(
            f"/api/runs/{run_id}/rear-video",
            files={"file": (name, content, "video/mp4")},
            headers={"X-Anon-Id": user},
        )


SIDE_RESULTS = {k: SAMPLE[k] for k in ("meta", "summary", "flags", "strides")}


# ---- POST /api/runs/{id}/rear-video ------------------------------------------------------
def test_rear_upload_stores_video_enqueues_and_leaves_the_side_run_untouched(env):
    run_id = env.make_run(status=RunStatus.processing)
    r = env.post_rear(run_id)
    assert r.status_code == 200 and r.json() == {"run_id": str(run_id), "rear_status": "processing"}
    assert env.uploads == [f"raw/{run_id}/rear.mp4"]
    env.delay.assert_called_once_with(str(run_id), f"raw/{run_id}/rear.mp4")
    (row,) = env.rear_rows(run_id)
    assert row.status == "processing" and row.results_json is None
    with env.Session() as db:
        run = db.get(Run, run_id)
        assert run.status == RunStatus.processing and run.results_json is None


def test_status_endpoint_reports_rear_status_independently(env):
    run_id = env.make_run(status=RunStatus.complete, results=SIDE_RESULTS)
    assert env.client.get(f"/api/runs/{run_id}/status").json()["rear_status"] is None
    env.post_rear(run_id)
    body = env.client.get(f"/api/runs/{run_id}/status").json()
    assert body["status"] == "complete" and body["rear_status"] == "processing"


def test_someone_elses_run_is_404_and_nothing_is_stored(env):
    run_id = env.make_run(user=OWNER)
    assert env.post_rear(run_id, user=STRANGER).status_code == 404
    assert env.uploads == [] and env.rear_rows(run_id) == []
    env.delay.assert_not_called()


def test_missing_run_and_missing_anon_id(env):
    assert env.post_rear(uuid.uuid4()).status_code == 404
    r = env.client.post(f"/api/runs/{env.make_run()}/rear-video", files={"file": ("r.mp4", MP4, "video/mp4")})
    assert r.status_code == 400


def test_consent_is_required(env):
    run_id = env.make_run()
    with env.Session() as db:
        db.query(ConsentRecord).filter(ConsentRecord.user_id == OWNER).delete()
        db.commit()
    r = env.post_rear(run_id)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "consent_required"
    assert env.uploads == []


def test_invalid_files_are_rejected_before_anything_is_stored(env):
    run_id = env.make_run()
    assert env.post_rear(run_id, content=b"not a video at all").status_code == 400
    assert env.post_rear(run_id, name="rear.avi").status_code == 400
    assert env.uploads == [] and env.rear_rows(run_id) == []


def test_second_rear_upload_is_a_409_and_does_not_overwrite(env):
    run_id = env.make_run()
    assert env.post_rear(run_id).status_code == 200
    r = env.post_rear(run_id)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "rear_video_exists"
    assert len(env.uploads) == 1 and len(env.rear_rows(run_id)) == 1


def test_failed_rear_video_can_be_retried_reusing_the_same_row(env):
    run_id = env.make_run()
    env.post_rear(run_id)
    with env.Session() as db:
        row = db.query(RunVideo).filter(RunVideo.run_id == run_id, RunVideo.view_type == "rear").one()
        row.status, row.error_message = "failed", "boom"
        db.commit()
    assert env.post_rear(run_id).status_code == 200
    (row,) = env.rear_rows(run_id)
    assert row.status == "processing" and row.error_message is None


def test_queue_outage_marks_the_rear_video_failed_and_retryable_not_stuck(env):
    run_id = env.make_run()
    env.delay.side_effect = RuntimeError("redis down")
    assert env.post_rear(run_id).status_code == 503
    (row,) = env.rear_rows(run_id)
    assert row.status == "failed"
    env.delay.side_effect = None
    assert env.post_rear(run_id).status_code == 200


def test_schema_enforces_one_rear_video_per_run(env):
    run_id = env.make_run()
    with env.Session() as db:
        db.add(RunVideo(run_id=run_id, view_type="rear", r2_key="a", status="processing"))
        db.commit()
        db.add(RunVideo(run_id=run_id, view_type="rear", r2_key="b", status="processing"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(RunVideo(run_id=run_id, view_type="top", r2_key="c"))
        with pytest.raises(IntegrityError):
            db.commit()


# ---- Side upload registers its side row -----------------------------------------------------
def test_create_run_registers_the_side_video_in_run_videos(env):
    r = env.client.post(
        "/api/runs",
        files={"file": ("input.mp4", MP4, "video/mp4")},
        data={"height_cm": "175"},
        headers={"X-Anon-Id": OWNER},
    )
    assert r.status_code == 200, r.text
    run_id = uuid.UUID(r.json()["run_id"])
    with env.Session() as db:
        (v,) = db.query(RunVideo).filter(RunVideo.run_id == run_id).all()
        assert v.view_type == "side" and v.r2_key == f"raw/{run_id}/input.mp4" and v.status is None


# ---- GET /api/runs/{id}: read-time merge ---------------------------------------------------------
def _attach_rear(env, run_id, status, results=None):
    with env.Session() as db:
        db.add(RunVideo(run_id=run_id, view_type="rear", r2_key=f"raw/{run_id}/rear.mp4", status=status, results_json=results))
        db.commit()


def test_single_view_run_response_is_unchanged(env):
    run_id = env.make_run(results=SIDE_RESULTS)
    results = env.client.get(f"/api/runs/{run_id}").json()["results"]
    assert results == SIDE_RESULTS and "rear_view" not in results and "schema_version" not in results


def test_run_with_both_views_returns_v2_with_rear_view_merged(env):
    run_id = env.make_run(results=SIDE_RESULTS)
    _attach_rear(env, run_id, "complete", REAR_VIEW)
    results = env.client.get(f"/api/runs/{run_id}").json()["results"]
    assert results["schema_version"] == 2 and results["rear_view"] == REAR_VIEW
    assert results["summary"] == SIDE_RESULTS["summary"]
    # The merge is read-time only — the stored side results are not rewritten.
    with env.Session() as db:
        assert "rear_view" not in db.get(Run, run_id).results_json


@pytest.mark.parametrize("row_status, expected", [
    ("processing", {"status": "processing"}),
    ("failed", {"status": "failed", "error": "rear_analysis_failed"}),
])
def test_pending_and_failed_rear_views_are_placeholders(env, row_status, expected):
    run_id = env.make_run(results=SIDE_RESULTS)
    _attach_rear(env, run_id, row_status)
    assert env.client.get(f"/api/runs/{run_id}").json()["results"]["rear_view"] == expected


def test_rear_result_does_not_appear_while_the_side_run_has_no_results(env):
    run_id = env.make_run(status=RunStatus.processing, results=None)
    _attach_rear(env, run_id, "complete", REAR_VIEW)
    assert env.client.get(f"/api/runs/{run_id}").json()["results"] is None


# ---- DELETE: storage-first, including the rear video ------------------------------------------------
def test_delete_removes_the_rear_video_from_storage_and_the_row(env):
    run_id = env.make_run()
    _attach_rear(env, run_id, "complete", REAR_VIEW)
    r = env.client.delete(f"/api/runs/{run_id}", headers={"X-Anon-Id": OWNER})
    assert r.status_code == 204
    assert set(env.deleted) == {
        f"raw/{run_id}/input.mp4", f"processed/{run_id}/annotated.mp4", f"raw/{run_id}/rear.mp4",
    }
    assert len(env.deleted) == 3  # the side raw key (on runs AND run_videos) is deleted once
    with env.Session() as db:
        assert db.query(Run).count() == 0 and db.query(RunVideo).count() == 0


def test_failed_rear_storage_delete_keeps_the_run_and_rows_so_it_can_be_retried(env, monkeypatch):
    run_id = env.make_run()
    _attach_rear(env, run_id, "complete", REAR_VIEW)

    def flaky(key):
        if key.endswith("rear.mp4"):
            raise RuntimeError("R2 unavailable")
    monkeypatch.setattr(main, "delete_object", flaky)
    r = env.client.delete(f"/api/runs/{run_id}", headers={"X-Anon-Id": OWNER})
    assert r.status_code == 502
    with env.Session() as db:
        assert db.query(Run).count() == 1 and db.query(RunVideo).count() == 2


def test_stranger_cannot_delete_or_view_rear_state_via_delete(env):
    run_id = env.make_run()
    _attach_rear(env, run_id, "complete", REAR_VIEW)
    assert env.client.delete(f"/api/runs/{run_id}", headers={"X-Anon-Id": STRANGER}).status_code == 404
    assert env.deleted == []

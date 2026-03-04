"""
Celery app and process_video task: download from R2, run job_runner, upload outputs, update DB.
"""
import os
import tempfile
import uuid
from pathlib import Path

import celery

from backend.database import get_db_session
from backend.job_runner import run_analysis
from backend.models import Run, RunStatus
from backend.storage import (
    annotated_video_key,
    dashboard_image_key,
    download_file,
    raw_video_key,
    upload_file,
)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = celery.Celery(
    "gait_analyzer",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]


def _update_progress(run_id: str, progress_pct: int) -> None:
    db = get_db_session()
    try:
        run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
        if run:
            run.progress_pct = progress_pct
            db.commit()
    finally:
        db.close()


@app.task(bind=True, name="backend.worker.process_video")
def process_video(self, run_id: str, raw_video_r2_key: str, height_cm: int) -> None:
    db = get_db_session()
    run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
    if not run:
        db.close()
        return
    temp_path = None
    try:
        temp_path = tempfile.mkdtemp(prefix="gait_")
        video_path = Path(temp_path) / "input.mp4"
        download_file(raw_video_r2_key, str(video_path))

        def on_progress(percent: float, message: str) -> None:
            _update_progress(run_id, int(min(percent, 100)))

        max_frames = None
        max_width = None
        try:
            nf = int(os.environ.get("GAIT_MAX_FRAMES", "0"))
            nw = int(os.environ.get("GAIT_MAX_WIDTH", "0"))
            max_frames = nf if nf > 0 else None
            max_width = nw if nw > 0 else None
        except ValueError:
            pass

        out = run_analysis(
            str(video_path),
            float(height_cm),
            progress_callback=on_progress,
            max_frames=max_frames,
            max_width=max_width,
        )

        ann_key = annotated_video_key(run_id)
        dash_key = dashboard_image_key(run_id)
        upload_file(out["annotated_video_path"], ann_key)
        upload_file(out["dashboard_path"], dash_key)

        run.annotated_video_r2_key = ann_key
        run.dashboard_image_r2_key = dash_key
        run.results_json = out["results"]
        run.status = RunStatus.complete
        run.progress_pct = 100
        run.error_message = None
        db.commit()

        for p in out.get("temp_paths") or []:
            try:
                os.unlink(p)
            except OSError:
                pass
    except Exception as e:
        run.status = RunStatus.failed
        run.error_message = str(e)
        run.progress_pct = 0
        db.commit()
        raise
    finally:
        db.close()
        if temp_path and os.path.isdir(temp_path):
            for f in Path(temp_path).iterdir():
                try:
                    f.unlink()
                except OSError:
                    pass
            try:
                os.rmdir(temp_path)
            except OSError:
                pass

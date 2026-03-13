"""
Celery app and process_video task: download from R2, preprocess, run job_runner, upload outputs, update DB.
"""
import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import celery

from backend.database import get_db_session
from backend.job_runner import run_analysis
from backend.models import Run, RunStatus
from backend.storage import (
    annotated_video_key,
    dashboard_image_key,
    download_file,
    upload_file,
)
from backend.video_preprocessor import preprocess_video

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = celery.Celery(
    "gait_analyzer",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
# Default to 1 to avoid OOM when API and worker share a container (CLI -c overrides this).
app.conf.worker_concurrency = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "1"))


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
    preprocessed_path = None
    try:
        temp_path = tempfile.mkdtemp(prefix="gait_")
        video_path = Path(temp_path) / "input.mp4"
        download_file(raw_video_r2_key, str(video_path))

        target_height = 720
        try:
            target_height = int(os.environ.get("VIDEO_MAX_HEIGHT", "720"))
        except ValueError:
            pass
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as preprocessed_fd:
            preprocessed_path = preprocessed_fd.name
        preprocess_meta = preprocess_video(
            str(video_path), preprocessed_path, target_height=target_height
        )
        run.preprocessing_meta = preprocess_meta
        raw_creation = preprocess_meta.get("creation_time_iso")
        run.recorded_at = (
            datetime.fromisoformat(raw_creation.replace("Z", "+00:00"))
            if raw_creation
            else None
        )
        db.commit()
        logger.info(
            "Preprocessing: %s -> %s, output_size_mb=%.1f",
            preprocess_meta.get("original_resolution"),
            preprocess_meta.get("output_resolution"),
            preprocess_meta.get("output_size_mb"),
        )

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
            preprocessed_path,
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
        if preprocessed_path and os.path.exists(preprocessed_path):
            try:
                os.unlink(preprocessed_path)
            except OSError:
                pass
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

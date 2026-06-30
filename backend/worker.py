"""
Celery app and process_video task: download from R2, preprocess, run job_runner, upload outputs, update DB.
"""
import atexit
import logging
import os
import signal
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import celery
import celery.exceptions
import sentry_sdk
from posthog import Posthog
from sentry_sdk.integrations.celery import CeleryIntegration

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

SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[CeleryIntegration()])

_POSTHOG_TOKEN = os.environ.get("POSTHOG_PROJECT_TOKEN", "").strip()
_POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com").strip()
posthog_client: Posthog | None = None
if _POSTHOG_TOKEN:
    posthog_client = Posthog(
        project_api_key=_POSTHOG_TOKEN,
        host=_POSTHOG_HOST,
        enable_exception_autocapture=True,
    )
    atexit.register(posthog_client.shutdown)

app = celery.Celery(
    "gait_analyzer",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
# Keep task results in Redis for 1 hour then expire them — prevents Redis filling up.
app.conf.result_expires = 3600
# Default to 1 to avoid OOM when API and worker share a container (CLI -c overrides this).
app.conf.worker_concurrency = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "1"))

# Track the run_id currently being processed so the SIGTERM handler can mark it failed.
_current_run_id: str | None = None


def _handle_sigterm(signum, frame):
    """On SIGTERM (Render deploy/scale-down), mark the in-flight run as failed so it
    doesn't stay stuck in 'processing' indefinitely."""
    if _current_run_id:
        try:
            db = get_db_session()
            run = db.query(Run).filter(Run.id == uuid.UUID(_current_run_id)).first()
            if run and run.status == RunStatus.processing:
                run.status = RunStatus.failed
                run.error_message = "Worker was restarted during processing. Please re-submit."
                db.commit()
            db.close()
        except Exception:
            pass  # Best-effort; the process is dying anyway
    raise SystemExit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)


def _update_progress(run_id: str, progress_pct: int) -> None:
    db = get_db_session()
    try:
        run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
        if run:
            run.progress_pct = progress_pct
            db.commit()
    finally:
        db.close()


# time_limit=600s (hard kill), soft_time_limit=540s (raises SoftTimeLimitExceeded first,
# allowing clean DB update before the hard kill fires).
@app.task(bind=True, name="backend.worker.process_video", time_limit=600, soft_time_limit=540)
def process_video(self, run_id: str, raw_video_r2_key: str, height_cm: int) -> None:
    global _current_run_id
    _current_run_id = run_id

    db = get_db_session()
    run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
    if not run:
        db.close()
        _current_run_id = None
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
        target_fps = None
        try:
            nf = int(os.environ.get("GAIT_MAX_FRAMES", "0"))
            nw = int(os.environ.get("GAIT_MAX_WIDTH", "0"))
            tf = float(os.environ.get("GAIT_TARGET_FPS", "0"))
            max_frames = nf if nf > 0 else None
            max_width = nw if nw > 0 else None
            target_fps = tf if tf > 0 else None
        except ValueError:
            pass

        out = run_analysis(
            preprocessed_path,
            float(height_cm),
            progress_callback=on_progress,
            max_frames=max_frames,
            max_width=max_width,
            target_fps=target_fps,
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

        if posthog_client and run.user_id:
            summary = (out["results"] or {}).get("summary") or {}
            posthog_client.capture(
                run.user_id,
                "run_completed",
                properties={
                    "height_cm": height_cm,
                    "cadence_avg": summary.get("cadence_avg"),
                    "flags_count": len((out["results"] or {}).get("flags") or []),
                },
            )

        for p in out.get("temp_paths") or []:
            try:
                os.unlink(p)
            except OSError:
                pass
    except celery.exceptions.SoftTimeLimitExceeded:
        run.status = RunStatus.failed
        run.error_message = "Analysis timed out (video may be too long or complex). Please try a shorter clip."
        run.progress_pct = 0
        db.commit()
        if posthog_client and run.user_id:
            posthog_client.capture(
                run.user_id,
                "run_failed",
                properties={"height_cm": height_cm, "error_type": "timeout"},
            )
        raise
    except Exception as e:
        run.status = RunStatus.failed
        run.error_message = str(e)
        run.progress_pct = 0
        db.commit()
        if posthog_client and run.user_id:
            posthog_client.capture(
                run.user_id,
                "run_failed",
                properties={"height_cm": height_cm, "error_type": type(e).__name__},
            )
        raise
    finally:
        _current_run_id = None
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

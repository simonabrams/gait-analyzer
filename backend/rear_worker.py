"""
Celery task for the optional rear-view video. Independent of the side-view
task in worker.py: separate task, separate queue, and it only ever touches
the `run_videos` rear row — never `runs`. A rear failure therefore cannot fail,
delay the completion of, refund, or otherwise affect the side-view analysis.

Routing: the task is bound to RUN_QUEUE. The worker must consume that queue
(`celery ... -Q celery,rear_view`, see render.yaml / docker-compose.yml) or
rear jobs will sit unprocessed. Today it's the same single-concurrency worker
as the side task, so the two run one after the other; giving RUN_QUEUE its own
worker service later is a deploy change only (see worker.py for why concurrency
is 1).
"""
import logging
import os
import tempfile
import uuid
from pathlib import Path

import celery.exceptions

from backend import worker as _worker
from backend.analytics import capture as posthog_capture
from backend.database import get_db_session
from backend.models import Run, RunVideo, VideoViewType
from backend.rear_job_runner import run_rear_analysis
from backend.storage import download_file
from backend.video_preprocessor import preprocess_video
from backend.worker import app

logger = logging.getLogger(__name__)

RUN_QUEUE = "rear_view"
TASK_NAME = "backend.rear_worker.process_rear_video"

# error_message is internal-only (the API never returns it — see
# results_schema.rear_view_from_video_row); cap it so a huge traceback string
# can't bloat the row.
_ERROR_MESSAGE_MAX = 500


def _rear_row(db, run_id: str) -> RunVideo | None:
    return (
        db.query(RunVideo)
        .filter(RunVideo.run_id == uuid.UUID(run_id), RunVideo.view_type == VideoViewType.rear.value)
        .first()
    )


def mark_rear_failed(db, row: RunVideo, error_message: str) -> None:
    """Fail ONLY the rear video. Deliberately does not touch runs.* or refund a
    free scan: the scan was paid for by (and delivered through) the side video."""
    row.status = "failed"
    row.error_message = error_message[:_ERROR_MESSAGE_MAX]
    db.commit()


def _capture(db, run_id: str, event: str, props: dict) -> None:
    """Product-usage analytics only — no body measurements or gait metrics
    (see /privacy: "pages viewed, features used")."""
    run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
    if run and run.user_id:
        posthog_capture(run.user_id, event, props)


def _limits_from_env():
    """GAIT_MAX_FRAMES/GAIT_MAX_WIDTH are shared with the side pipeline (worker.py) —
    same memory ceiling applies to either video. Target fps is NOT shared: a rear
    gait cycle is only ~10-11 frames at the side pipeline's proven GAIT_TARGET_FPS
    (e.g. 15), which is too coarse for the initial-contact/mid-stance windows
    rear_metrics measures (see rear_metrics.py's cycle-segmentation comments).
    GAIT_REAR_TARGET_FPS overrides just this pipeline; unset, it falls back to
    GAIT_TARGET_FPS so today's behavior is unchanged until someone sets it."""
    max_frames = max_width = target_fps = None
    try:
        nf = int(os.environ.get("GAIT_MAX_FRAMES", "0"))
        nw = int(os.environ.get("GAIT_MAX_WIDTH", "0"))
        raw_tf = os.environ.get("GAIT_REAR_TARGET_FPS") or os.environ.get("GAIT_TARGET_FPS", "0")
        tf = float(raw_tf)
        max_frames = nf if nf > 0 else None
        max_width = nw if nw > 0 else None
        target_fps = tf if tf > 0 else None
    except ValueError:
        pass
    return max_frames, max_width, target_fps


@app.task(bind=True, name=TASK_NAME, queue=RUN_QUEUE, time_limit=600, soft_time_limit=540)
def process_rear_video(self, run_id: str, rear_video_r2_key: str) -> None:
    _worker._current_rear_run_id = run_id
    db = get_db_session()
    row = _rear_row(db, run_id)
    if not row or row.status == "complete":
        # Row deleted with its run, or a redelivered task that already finished.
        db.close()
        _worker._current_rear_run_id = None
        return

    temp_dir = None
    preprocessed_path = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="gait_rear_")
        video_path = Path(temp_dir) / "rear.mp4"
        download_file(rear_video_r2_key, str(video_path))

        try:
            target_height = int(os.environ.get("VIDEO_MAX_HEIGHT", "720"))
        except ValueError:
            target_height = 720
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as fd:
            preprocessed_path = fd.name
        preprocess_video(str(video_path), preprocessed_path, target_height=target_height)

        max_frames, max_width, target_fps = _limits_from_env()
        out = run_rear_analysis(
            preprocessed_path, max_frames=max_frames, max_width=max_width, target_fps=target_fps
        )
        rear_view = out["rear_view"]
        if out["truncated"]:
            rear_view["meta"]["truncated_frames"] = max_frames
            rear_view["meta"]["frames_used"] = out["frames_used"]

        # "complete" is pipeline state (the task ran); whether the analysis was
        # usable lives in rear_view["status"] (ok / low_confidence / insufficient_data).
        row.results_json = rear_view
        row.status = "complete"
        row.error_message = None
        db.commit()
        _capture(db, run_id, "rear_run_completed", {
            "rear_status": rear_view["status"],
            "reason": (rear_view.get("confidence_gate") or {}).get("reason"),
        })
    except celery.exceptions.SoftTimeLimitExceeded:
        mark_rear_failed(db, row, "Rear-view analysis timed out (video may be too long or complex).")
        _capture(db, run_id, "rear_run_failed", {"error_type": "timeout"})
        raise
    except Exception as e:
        mark_rear_failed(db, row, str(e))
        _capture(db, run_id, "rear_run_failed", {"error_type": type(e).__name__})
        raise
    finally:
        _worker._current_rear_run_id = None
        db.close()
        if preprocessed_path and os.path.exists(preprocessed_path):
            try:
                os.unlink(preprocessed_path)
            except OSError:
                pass
        if temp_dir and os.path.isdir(temp_dir):
            for f in Path(temp_dir).iterdir():
                try:
                    f.unlink()
                except OSError:
                    pass
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass

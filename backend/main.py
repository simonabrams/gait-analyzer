"""
FastAPI app: runs API, health, CORS.
"""
import logging
import os
import tempfile
import uuid
from typing import List

from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from backend import storage
from backend.database import get_db
from backend.models import Run, RunStatus
from backend.schemas import (
    RunCreatedResponse,
    RunDetail,
    RunListItem,
    RunStatusResponse,
)
from backend.storage import (
    annotated_video_key,
    dashboard_image_key,
    delete_object,
    generate_presigned_url,
    raw_video_key,
    upload_file,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gait Analyzer API")

_default_origins = "http://localhost:3000,http://127.0.0.1:3000,https://runlens.vercel.app"
origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", _default_origins).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."},
    )

ALLOWED_EXTENSIONS = {"mp4", "mov"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


def _get_run(db: Session, run_id: uuid.UUID) -> Run | None:
    return db.query(Run).filter(Run.id == run_id).first()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/local-artifacts/{run_id}/{filename}")
def serve_local_artifact(run_id: str, filename: str):
    if filename not in ("annotated.mp4", "dashboard.png") or ".." in run_id or "/" in run_id:
        raise HTTPException(404, "Not found")
    if not storage.LOCAL_STORAGE_PATH:
        raise HTTPException(404, "Not found")
    root = Path(storage.LOCAL_STORAGE_PATH).resolve()
    path = (root / "processed" / run_id / filename).resolve()
    if not path.is_file() or not str(path).startswith(str(root)):
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="video/mp4" if filename.endswith(".mp4") else "image/png")


@app.post("/api/runs", response_model=RunCreatedResponse)
def create_run(
    file: UploadFile = File(...),
    height_cm: int = Form(..., ge=100, le=250),
    db: Session = Depends(get_db),
):
    suffix = (file.filename or "").split(".")[-1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only MP4 and MOV files are allowed")
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    run_id = uuid.uuid4()
    raw_key = raw_video_key(str(run_id))
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        upload_file(tmp_path, raw_key)
    except RuntimeError as e:
        if "R2" in str(e) or "LOCAL_STORAGE" in str(e):
            raise HTTPException(
                503,
                "Storage not configured. Set LOCAL_STORAGE_PATH (e.g. .local_storage) or R2 credentials.",
            ) from e
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    run = Run(
        id=run_id,
        height_cm=height_cm,
        status=RunStatus.processing,
        progress_pct=0,
        raw_video_r2_key=raw_key,
    )
    db.add(run)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("DB commit failed: %s", e)
        raise HTTPException(500, "Database error. Check server logs.") from e
    try:
        from backend.worker import process_video
        process_video.delay(str(run_id), raw_key, height_cm)
    except Exception as e:
        logger.exception("Failed to enqueue job: %s", e)
        raise HTTPException(
            503,
            "Job queue unavailable. Is Redis running?",
        ) from e
    return RunCreatedResponse(run_id=run_id, status="processing")


@app.get("/api/runs/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    preprocessing_warning = None
    if (run.preprocessing_meta or {}).get("was_trimmed"):
        preprocessing_warning = "Video trimmed to 3 minutes"
    return RunStatusResponse(
        status=run.status.value,
        progress=run.progress_pct or 0,
        preprocessing_warning=preprocessing_warning,
    )


@app.get("/api/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    detail = RunDetail(
        run_id=run.id,
        created_at=run.created_at,
        height_cm=run.height_cm,
        status=run.status.value,
        results=run.results_json,
        error_message=run.error_message,
    )
    if run.status == RunStatus.complete and run.results_json:
        if run.annotated_video_r2_key:
            detail.annotated_video_url = generate_presigned_url(run.annotated_video_r2_key)
        if run.dashboard_image_r2_key:
            detail.dashboard_image_url = generate_presigned_url(run.dashboard_image_r2_key)
    return detail


@app.get("/api/runs", response_model=List[RunListItem])
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(Run).order_by(Run.created_at.desc()).all()
    out = []
    for r in runs:
        summary = (r.results_json or {}).get("summary") or {}
        flags = (r.results_json or {}).get("flags") or []
        out.append(
            RunListItem(
                run_id=r.id,
                created_at=r.created_at,
                cadence_avg=summary.get("cadence_avg"),
                vertical_osc_avg_cm=summary.get("vertical_osc_avg_cm"),
                knee_angle_strike_avg_deg=summary.get("knee_angle_strike_avg_deg"),
                flags_count=len(flags),
            )
        )
    return out


@app.delete("/api/runs/{run_id}", status_code=204)
def delete_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    for key in [run.raw_video_r2_key, run.annotated_video_r2_key, run.dashboard_image_r2_key]:
        if key:
            delete_object(key)
    db.delete(run)
    db.commit()
    return None

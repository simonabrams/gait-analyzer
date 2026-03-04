"""
FastAPI app: runs API, health, CORS.
"""
import os
import uuid
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

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

app = FastAPI(title="Gait Analyzer API")

origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").strip().split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {"mp4", "mov"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


def _get_run(db: Session, run_id: uuid.UUID) -> Run | None:
    return db.query(Run).filter(Run.id == run_id).first()


@app.get("/api/health")
def health():
    return {"status": "ok"}


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
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        upload_file(tmp_path, raw_key)
    finally:
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
    db.commit()
    from backend.worker import process_video
    process_video.delay(str(run_id), raw_key, height_cm)
    return RunCreatedResponse(run_id=run_id, status="processing")


@app.get("/api/runs/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return RunStatusResponse(status=run.status.value, progress=run.progress_pct or 0)


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

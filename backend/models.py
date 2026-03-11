"""
SQLAlchemy ORM models for gait analyzer.
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RunStatus(str, enum.Enum):
    processing = "processing"
    complete = "complete"
    failed = "failed"


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    height_cm = Column(Integer, nullable=False)
    status = Column(Enum(RunStatus), nullable=False, default=RunStatus.processing)
    progress_pct = Column(Integer, default=0, nullable=False)
    raw_video_r2_key = Column(String(512), nullable=True)
    annotated_video_r2_key = Column(String(512), nullable=True)
    dashboard_image_r2_key = Column(String(512), nullable=True)
    results_json = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    preprocessing_meta = Column(JSONB, nullable=True)

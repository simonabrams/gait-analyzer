"""
Pydantic request/response schemas.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RunCreate(BaseModel):
    height_cm: int


class RunStatusResponse(BaseModel):
    status: str
    progress: int


class RunListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    created_at: datetime
    cadence_avg: Optional[float] = None
    vertical_osc_avg_cm: Optional[float] = None
    knee_angle_strike_avg_deg: Optional[float] = None
    flags_count: int = 0


class RunCreatedResponse(BaseModel):
    run_id: UUID
    status: str = "processing"


class RunDetail(BaseModel):
    run_id: UUID
    created_at: datetime
    height_cm: int
    status: str
    results: Optional[dict[str, Any]] = None
    annotated_video_url: Optional[str] = None
    dashboard_image_url: Optional[str] = None
    error_message: Optional[str] = None

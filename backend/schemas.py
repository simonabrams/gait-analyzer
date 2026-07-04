"""
Pydantic request/response schemas.
"""
from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RunCreate(BaseModel):
    height_cm: int


class RunStatusResponse(BaseModel):
    status: str
    progress: int
    preprocessing_warning: Optional[str] = None


class RunListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    created_at: datetime
    recorded_at: Optional[datetime] = None
    cadence_avg: Optional[float] = None
    vertical_osc_avg_cm: Optional[float] = None
    knee_angle_strike_avg_deg: Optional[float] = None
    flags_count: int = 0


class RunListResponse(BaseModel):
    total: int
    items: List[RunListItem]


class RunCreatedResponse(BaseModel):
    run_id: UUID
    status: str = "processing"


class RunDetail(BaseModel):
    run_id: UUID
    created_at: datetime
    recorded_at: Optional[datetime] = None
    height_cm: int
    status: str
    results: Optional[dict[str, Any]] = None
    annotated_video_url: Optional[str] = None
    dashboard_image_url: Optional[str] = None
    error_message: Optional[str] = None


class CheckoutRequest(BaseModel):
    plan: Literal["monthly", "yearly"]


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


class BillingStatusResponse(BaseModel):
    tier: str
    status: Optional[str] = None
    is_pro: bool
    trial_end: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    free_scans_used: int
    free_scans_limit: int = 1
    bonus_scans: int = 0
    referral_code: str
    referral_link: str

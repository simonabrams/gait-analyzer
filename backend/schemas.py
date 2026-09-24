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
    # State of the optional rear-view video: None (no rear video),
    # "processing", "complete" or "failed". Independent of `status`.
    rear_status: Optional[str] = None
    # True only when the caller's resolved identity (Clerk user or anon id,
    # whichever credential was sent — see anon.resolve_user_id_optional)
    # matches this run's owner. This endpoint is public and callable with no
    # credentials at all (e.g. a stranger viewing a shared link), in which
    # case this is always False rather than raising.
    is_owner: bool = False


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


class RearVideoCreatedResponse(BaseModel):
    run_id: UUID
    rear_status: str = "processing"


class RunDetail(BaseModel):
    run_id: UUID
    created_at: datetime
    recorded_at: Optional[datetime] = None
    height_cm: int
    status: str
    results: Optional[dict[str, Any]] = None
    annotated_video_url: Optional[str] = None
    dashboard_image_url: Optional[str] = None
    # Skeleton-overlay rear-view video, set only once a rear video exists and
    # has finished processing (mirrors annotated_video_url's gating).
    rear_video_url: Optional[str] = None
    error_message: Optional[str] = None


class ConsentStatusResponse(BaseModel):
    policy_version: str
    consented: bool
    consented_at: Optional[datetime] = None


class ConsentAcceptRequest(BaseModel):
    policy_version: str
    # Required (must be True) for every user, signed in or not — nothing
    # upstream of this establishes age today.
    age_confirmed: bool = False


class ClaimRequest(BaseModel):
    anon_id: str


class ClaimResponse(BaseModel):
    claimed_runs: int
    consent_claimed: bool
    free_scans_merged: int


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

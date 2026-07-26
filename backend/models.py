"""
SQLAlchemy ORM models for gait analyzer.
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Enum, Index, Integer, String, Text
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
    recorded_at = Column(DateTime(timezone=True), nullable=True)
    # Clerk user ID (e.g. "user_2abc..."). Nullable for pre-auth legacy runs.
    user_id = Column(String(255), nullable=True, index=True)

    __table_args__ = (
        Index("ix_runs_user_id_created_at", "user_id", "created_at"),
    )


class ConsentRecord(Base):
    """Audit log of privacy-policy consent: one row per (user, policy version)
    acceptance. Rows are append-only and must survive run deletion — they are
    the proof that processing was consented to. Whether they survive *account*
    deletion is a counsel question (see docs/trust/02-privacy-policy.md §9)."""
    __tablename__ = "consent_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Clerk user ID (e.g. "user_2abc...").
    user_id = Column(String(255), nullable=False, index=True)
    # Version identifier of the policy text consented to (see backend/consent.py).
    policy_version = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # Re-POSTing consent for the same version is a no-op, not a new row.
        Index("ix_consent_records_user_id_policy_version", "user_id", "policy_version", unique=True),
    )


class SubscriptionTier(str, enum.Enum):
    free = "free"
    pro = "pro"
    # elite = "elite"  # roadmap — add here only, no migration needed (see Subscription.tier below)


class SubscriptionStatus(str, enum.Enum):
    """Mirrors Stripe's own subscription status strings, plus an internal-only
    'grandfathered' used for the pre-launch backfill (see migration 007)."""
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"
    grandfathered = "grandfathered"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Clerk user ID. One subscription row per user, created lazily on first use.
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    # Plain strings (not a Postgres native Enum, unlike RunStatus above) so that
    # adding a new tier (e.g. "elite") later is an app-code change, not a migration —
    # native Postgres enums require ALTER TYPE ... ADD VALUE outside a transaction.
    tier = Column(String(20), nullable=False, default=SubscriptionTier.free.value)
    status = Column(String(20), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True, index=True)
    price_id = Column(String(100), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    # Lifetime free-tier scan counter (not COUNT(runs) — deleting a run must not
    # refund the free scan). Free-tier gate: free_scans_used >= 1 + bonus_scans.
    free_scans_used = Column(Integer, default=0, nullable=False)
    # Extra free scans earned via referrals.
    bonus_scans = Column(Integer, default=0, nullable=False)
    referral_code = Column(String(16), nullable=False, unique=True, index=True)
    # Set once, at most, when this user's first run is created with a valid
    # referral code attached. Guards against re-claiming on later runs.
    referred_by_code = Column(String(16), nullable=True)
    # Flips to True when the referral bonus is actually paid out (on this user's
    # first completed run), preventing double-grants across multiple runs.
    referral_bonus_granted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

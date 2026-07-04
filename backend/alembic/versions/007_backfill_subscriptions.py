"""Backfill subscriptions for pre-launch users (grandfathered Pro transition)

Data-only migration: every user with at least one existing run gets 60 days
of full Pro access as a goodwill transition, since they already used a free
scan under the old (unlimited) model. Users with no prior runs are left to
the normal lazy free-tier path (billing.get_or_create_subscription).

Revision ID: 007
Revises: 006
Create Date: 2026-07-01

"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    user_ids = [
        row[0]
        for row in conn.execute(
            sa.text("SELECT DISTINCT user_id FROM runs WHERE user_id IS NOT NULL")
        ).fetchall()
    ]
    if not user_ids:
        return

    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=60)
    insert_stmt = sa.text(
        """
        INSERT INTO subscriptions (
            id, user_id, tier, status, current_period_end,
            free_scans_used, bonus_scans, referral_code,
            referral_bonus_granted, cancel_at_period_end,
            created_at, updated_at
        )
        VALUES (
            :id, :user_id, 'pro', 'grandfathered', :period_end,
            1, 0, :referral_code,
            false, false,
            :now, :now
        )
        ON CONFLICT (user_id) DO NOTHING
        """
    )
    for user_id in user_ids:
        conn.execute(
            insert_stmt,
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "period_end": period_end,
                "referral_code": uuid.uuid4().hex[:10],
                "now": now,
            },
        )


def downgrade() -> None:
    op.execute("DELETE FROM subscriptions WHERE status = 'grandfathered'")

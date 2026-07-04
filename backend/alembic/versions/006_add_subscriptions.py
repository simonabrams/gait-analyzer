"""Add subscriptions table for paid tiers

Revision ID: 006
Revises: 005
Create Date: 2026-07-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("price_id", sa.String(100), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("free_scans_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bonus_scans", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referral_code", sa.String(16), nullable=False),
        sa.Column("referred_by_code", sa.String(16), nullable=True),
        sa.Column("referral_bonus_granted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)
    op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"])
    op.create_index(
        "ix_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"], unique=True
    )
    op.create_index("ix_subscriptions_referral_code", "subscriptions", ["referral_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_subscriptions_referral_code", table_name="subscriptions")
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

"""Add consent_records table for privacy-policy consent logging

Revision ID: 008
Revises: 007
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index(
        "ix_consent_records_user_id_policy_version",
        "consent_records",
        ["user_id", "policy_version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_consent_records_user_id_policy_version", table_name="consent_records")
    op.drop_index("ix_consent_records_user_id", table_name="consent_records")
    op.drop_table("consent_records")

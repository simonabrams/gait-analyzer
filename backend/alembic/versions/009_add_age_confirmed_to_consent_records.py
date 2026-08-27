"""Add age_confirmed to consent_records

Revision ID: 009
Revises: 008
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "consent_records",
        sa.Column("age_confirmed", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consent_records", "age_confirmed")

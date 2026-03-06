"""Add preprocessing_meta to runs

Revision ID: 002
Revises: 001
Create Date: 2025-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("preprocessing_meta", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("runs", "preprocessing_meta")

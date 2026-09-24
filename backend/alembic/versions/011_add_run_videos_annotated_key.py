"""Add annotated_r2_key to run_videos

Revision ID: 011
Revises: 010
Create Date: 2026-09-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "run_videos",
        sa.Column("annotated_r2_key", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("run_videos", "annotated_r2_key")

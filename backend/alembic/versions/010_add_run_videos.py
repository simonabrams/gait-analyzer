"""Add run_videos (view_type side|rear) and backfill side rows

Revision ID: 010
Revises: 009
Create Date: 2026-09-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "run_videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("view_type", sa.String(16), nullable=False),
        sa.Column("r2_key", sa.String(512), nullable=False),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("results_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("view_type IN ('side', 'rear')", name="ck_run_videos_view_type"),
    )
    op.create_index(
        "ix_run_videos_run_id_view_type", "run_videos", ["run_id", "view_type"], unique=True
    )

    # Existing single-view runs stay valid as-is: every run that has a stored
    # raw video gets a side row pointing at it. runs.raw_video_r2_key remains
    # the authoritative side key for the side pipeline; side rows carry no
    # status/results (those stay on runs).
    op.execute(
        """
        INSERT INTO run_videos (id, run_id, view_type, r2_key, created_at)
        SELECT gen_random_uuid(), id, 'side', raw_video_r2_key, created_at
        FROM runs
        WHERE raw_video_r2_key IS NOT NULL
        """
    )


def downgrade() -> None:
    # Drops rear rows (and their status/results) with the table. Rear videos in
    # storage are NOT deleted by a downgrade — clean up raw/<run_id>/rear.mp4 by hand.
    op.drop_index("ix_run_videos_run_id_view_type", table_name="run_videos")
    op.drop_table("run_videos")

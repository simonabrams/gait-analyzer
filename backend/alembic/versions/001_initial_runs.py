"""Initial runs table

Revision ID: 001
Revises:
Create Date: 2025-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    run_status = postgresql.ENUM(
        "processing", "complete", "failed",
        name="runstatus",
        create_type=True,
    )
    run_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("processing", "complete", "failed", name="runstatus"), nullable=False, server_default="processing"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_video_r2_key", sa.String(512), nullable=True),
        sa.Column("annotated_video_r2_key", sa.String(512), nullable=True),
        sa.Column("dashboard_image_r2_key", sa.String(512), nullable=True),
        sa.Column("results_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("runs")
    op.execute("DROP TYPE runstatus")

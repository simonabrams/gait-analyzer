"""Add user_id to runs for per-user ownership

Revision ID: 005
Revises: 004
Create Date: 2026-03-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("user_id", sa.String(255), nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_runs_user_id ON runs (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_runs_user_id_created_at ON runs (user_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_runs_user_id_created_at")
    op.execute("DROP INDEX IF EXISTS ix_runs_user_id")
    op.drop_column("runs", "user_id")

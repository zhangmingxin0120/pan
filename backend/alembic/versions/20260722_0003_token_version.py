"""invalidate sessions after password changes

Revision ID: 20260722_0003
Revises: 20260722_0002
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0003"
down_revision = "20260722_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")


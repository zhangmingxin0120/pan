"""drop legacy api write permission

Revision ID: 20260723_0010
Revises: 20260723_0009
Create Date: 2026-07-23 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0010"
down_revision = "20260723_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("api_applications", "can_write")


def downgrade() -> None:
    op.add_column(
        "api_applications",
        sa.Column("can_write", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute("UPDATE api_applications SET can_write = can_upload OR can_manage")

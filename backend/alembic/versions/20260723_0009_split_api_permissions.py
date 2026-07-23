"""split api permissions

Revision ID: 20260723_0009
Revises: 20260722_0008
Create Date: 2026-07-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0009"
down_revision = "20260722_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_applications",
        sa.Column("can_download", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "api_applications",
        sa.Column("can_upload", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "api_applications",
        sa.Column("can_manage", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute("UPDATE api_applications SET can_download = can_read")
    op.execute("UPDATE api_applications SET can_upload = can_write, can_manage = can_write")


def downgrade() -> None:
    op.drop_column("api_applications", "can_manage")
    op.drop_column("api_applications", "can_upload")
    op.drop_column("api_applications", "can_download")

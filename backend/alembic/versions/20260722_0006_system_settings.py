"""add runtime system settings

Revision ID: 20260722_0006
Revises: 20260722_0005
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0006"
down_revision = "20260722_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("registration_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_system_settings_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO system_settings (id, registration_enabled) VALUES (1, true)"
        )
    )


def downgrade() -> None:
    op.drop_table("system_settings")

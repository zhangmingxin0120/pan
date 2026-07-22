"""enforce case-insensitive email uniqueness

Revision ID: 20260722_0002
Revises: 20260722_0001
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0002"
down_revision = "20260722_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_users_email_lower", table_name="users")


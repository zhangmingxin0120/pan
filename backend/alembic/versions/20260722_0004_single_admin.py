"""add the single administrator role

Revision ID: 20260722_0004
Revises: 20260722_0003
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0004"
down_revision = "20260722_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column(
        "users", sa.Column("must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_index("uq_users_username_lower", "users", [sa.text("lower(username)")], unique=True)
    op.create_index(
        "uq_users_single_admin",
        "users",
        ["is_admin"],
        unique=True,
        postgresql_where=sa.text("is_admin = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_single_admin", table_name="users")
    op.drop_index("uq_users_username_lower", table_name="users")
    op.drop_column("users", "is_active")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "is_admin")
    op.drop_column("users", "username")

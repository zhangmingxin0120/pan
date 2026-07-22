"""add lightweight external API applications

Revision ID: 20260722_0007
Revises: 20260722_0006
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0007"
down_revision = "20260722_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("root_node_id", sa.Uuid(), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("can_read", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("can_write", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_delete", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("request_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("failed_request_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("upload_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("download_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["root_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_applications_key_prefix", "api_applications", ["key_prefix"], unique=True)
    op.create_index("ix_api_applications_root_node_id", "api_applications", ["root_node_id"])
    op.create_index("ix_api_applications_user_id", "api_applications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_api_applications_user_id", table_name="api_applications")
    op.drop_index("ix_api_applications_root_node_id", table_name="api_applications")
    op.drop_index("ix_api_applications_key_prefix", table_name="api_applications")
    op.drop_table("api_applications")

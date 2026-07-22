"""initial schema

Revision ID: 20260722_0001
Revises:
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    node_kind = sa.Enum("FILE", "FOLDER", name="node_kind")
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("quota_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("original_parent_id", sa.Uuid(), nullable=True),
        sa.Column("kind", node_kind, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_root", sa.Boolean(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("storage_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("trashed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("size_bytes >= 0", name="ck_nodes_non_negative_size"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_nodes_owner_parent", "nodes", ["owner_id", "parent_id"])
    op.create_index("ix_nodes_owner_trashed", "nodes", ["owner_id", "trashed_at"])
    op.create_index(
        "uq_nodes_active_sibling_name",
        "nodes",
        ["owner_id", "parent_id", sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("trashed_at IS NULL AND is_root = false"),
    )
    op.create_table(
        "shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shares_node_id", "shares", ["node_id"])
    op.create_index("ix_shares_owner_id", "shares", ["owner_id"])
    op.create_index("ix_shares_token", "shares", ["token"], unique=True)


def downgrade() -> None:
    op.drop_table("shares")
    op.drop_table("nodes")
    op.drop_table("users")
    sa.Enum(name="node_kind").drop(op.get_bind())

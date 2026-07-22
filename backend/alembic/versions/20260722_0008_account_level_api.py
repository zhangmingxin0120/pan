"""make API applications account scoped

Revision ID: 20260722_0008
Revises: 20260722_0007
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0008"
down_revision = "20260722_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_api_applications_root_node_id", table_name="api_applications")
    op.drop_column("api_applications", "root_node_id")


def downgrade() -> None:
    op.add_column(
        "api_applications", sa.Column("root_node_id", sa.Uuid(), nullable=True)
    )
    op.execute(
        sa.text(
            "UPDATE api_applications AS app "
            "SET root_node_id = root.id FROM nodes AS root "
            "WHERE root.owner_id = app.user_id AND root.is_root = true"
        )
    )
    op.alter_column("api_applications", "root_node_id", nullable=False)
    op.create_foreign_key(
        "api_applications_root_node_id_fkey",
        "api_applications",
        "nodes",
        ["root_node_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_api_applications_root_node_id",
        "api_applications",
        ["root_node_id"],
    )

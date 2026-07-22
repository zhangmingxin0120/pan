"""allow permanent shares and change the default quota to 5 GiB

Revision ID: 20260722_0005
Revises: 20260722_0004
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722_0005"
down_revision = "20260722_0004"
branch_labels = None
depends_on = None

OLD_DEFAULT_QUOTA = 10 * 1024 * 1024 * 1024
NEW_DEFAULT_QUOTA = 5 * 1024 * 1024 * 1024


def upgrade() -> None:
    op.alter_column(
        "shares",
        "expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )
    op.execute(
        sa.text(
            "UPDATE users SET quota_bytes = :new_quota "
            "WHERE is_admin = false AND quota_bytes = :old_quota"
        ).bindparams(new_quota=NEW_DEFAULT_QUOTA, old_quota=OLD_DEFAULT_QUOTA)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE shares SET expires_at = now() + interval '365 days' WHERE expires_at IS NULL"
        )
    )
    op.alter_column(
        "shares",
        "expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.execute(
        sa.text(
            "UPDATE users SET quota_bytes = :old_quota "
            "WHERE is_admin = false AND quota_bytes = :new_quota"
        ).bindparams(old_quota=OLD_DEFAULT_QUOTA, new_quota=NEW_DEFAULT_QUOTA)
    )

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NodeKind(str, enum.Enum):
    FILE = "file"
    FOLDER = "folder"


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_nodes_non_negative_size"),
        Index("ix_nodes_owner_parent", "owner_id", "parent_id"),
        Index("ix_nodes_owner_trashed", "owner_id", "trashed_at"),
        Index(
            "uq_nodes_active_sibling_name",
            "owner_id",
            "parent_id",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("trashed_at IS NULL AND is_root = false"),
            sqlite_where=text("trashed_at IS NULL AND is_root = 0"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True
    )
    original_parent_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    kind: Mapped[NodeKind] = mapped_column(Enum(NodeKind, name="node_kind"))
    name: Mapped[str] = mapped_column(String(255))
    is_root: Mapped[bool] = mapped_column(Boolean, default=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    trashed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="nodes")
    parent: Mapped["Node | None"] = relationship(
        remote_side="Node.id", foreign_keys=[parent_id], back_populates="children"
    )
    children: Mapped[list["Node"]] = relationship(
        back_populates="parent", foreign_keys=[parent_id], passive_deletes=True
    )
    shares: Mapped[list["Share"]] = relationship(back_populates="node", cascade="all, delete-orphan")


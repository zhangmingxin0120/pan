import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApiApplication(Base):
    __tablename__ = "api_applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    root_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), index=True
    )
    key_prefix: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(String(64))
    can_read: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    can_write: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    request_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    failed_request_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    upload_bytes: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    download_bytes: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="api_applications")
    root_node: Mapped["Node"] = relationship()

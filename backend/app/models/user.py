import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("uq_users_email_lower", func.lower(text("email")), unique=True),
        Index("uq_users_username_lower", func.lower(text("username")), unique=True),
        Index(
            "uq_users_single_admin",
            "is_admin",
            unique=True,
            postgresql_where=text("is_admin = true"),
            sqlite_where=text("is_admin = 1"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    quota_bytes: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )

    nodes: Mapped[list["Node"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    shares: Mapped[list["Share"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    api_applications: Mapped[list["ApiApplication"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

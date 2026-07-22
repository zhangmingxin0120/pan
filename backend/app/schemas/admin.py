import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AdminOverviewResponse(BaseModel):
    user_count: int
    active_user_count: int
    file_count: int
    storage_bytes: int


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    is_active: bool
    quota_bytes: int
    used_bytes: int
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int


class AdminUserUpdateRequest(BaseModel):
    is_active: bool | None = None
    quota_bytes: int | None = Field(default=None, ge=0)

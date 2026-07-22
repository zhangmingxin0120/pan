import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AdminOverviewResponse(BaseModel):
    user_count: int
    active_user_count: int
    file_count: int
    storage_bytes: int
    disk_total_bytes: int
    disk_free_bytes: int


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


class AdminUserCreateRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    quota_bytes: int | None = Field(default=None, ge=0)


class AdminUserCreateResponse(BaseModel):
    user: AdminUserResponse
    temporary_password: str


class AdminPasswordResetResponse(BaseModel):
    temporary_password: str


class AdminPasswordResetRequest(BaseModel):
    password: str = Field(default="123456", min_length=6, max_length=128)


class AdminSettingsResponse(BaseModel):
    registration_enabled: bool


class AdminSettingsUpdateRequest(BaseModel):
    registration_enabled: bool

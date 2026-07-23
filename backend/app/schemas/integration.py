import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.node import NodeResponse


class ApiApplicationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    user_id: uuid.UUID
    can_read: bool = True
    can_download: bool = False
    can_upload: bool = False
    can_manage: bool = False
    can_delete: bool = False

    @model_validator(mode="after")
    def require_permission(self):
        if not (
            self.can_read
            or self.can_download
            or self.can_upload
            or self.can_manage
            or self.can_delete
        ):
            raise ValueError("至少选择一项接口权限")
        return self


class ApiApplicationUpdateRequest(BaseModel):
    is_active: bool | None = None
    can_read: bool | None = None
    can_download: bool | None = None
    can_upload: bool | None = None
    can_manage: bool | None = None
    can_delete: bool | None = None


class ApiApplicationResponse(BaseModel):
    id: uuid.UUID
    name: str
    user_id: uuid.UUID
    user_email: str
    key_prefix: str
    can_read: bool
    can_download: bool
    can_upload: bool
    can_manage: bool
    can_delete: bool
    is_active: bool
    request_count: int
    failed_request_count: int
    upload_bytes: int
    download_bytes: int
    last_used_at: datetime | None
    created_at: datetime


class ApiApplicationListResponse(BaseModel):
    items: list[ApiApplicationResponse]
    total: int


class ApiApplicationSecretResponse(BaseModel):
    application: ApiApplicationResponse
    api_key: str


class ApiKeyRotateResponse(BaseModel):
    api_key: str


class FindListResponse(BaseModel):
    items: list[NodeResponse]
    total: int

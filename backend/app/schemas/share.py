import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.node import BreadcrumbItem, NodeResponse


class ShareCreateRequest(BaseModel):
    node_id: uuid.UUID
    expires_in_days: int | None = Field(default=7, ge=1, le=365)


class ShareResponse(BaseModel):
    id: uuid.UUID
    token: str
    node: NodeResponse
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    is_active: bool


class ShareListResponse(BaseModel):
    items: list[ShareResponse]
    total: int
    page: int
    page_size: int


class PublicShareResponse(BaseModel):
    token: str
    root: NodeResponse
    current_folder: NodeResponse | None
    breadcrumbs: list[BreadcrumbItem]
    items: list[NodeResponse]
    expires_at: datetime | None
    owner_name: str

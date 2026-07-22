import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import NodeKind


class NodeResponse(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    kind: NodeKind
    name: str
    is_root: bool
    size_bytes: int
    content_type: str | None
    created_at: datetime
    updated_at: datetime
    trashed_at: datetime | None

    model_config = {"from_attributes": True}


class BreadcrumbItem(BaseModel):
    id: uuid.UUID
    name: str


class NodeListResponse(BaseModel):
    items: list[NodeResponse]
    total: int
    page: int
    page_size: int
    breadcrumbs: list[BreadcrumbItem]
    current_folder: NodeResponse


class FolderCreateRequest(BaseModel):
    parent_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)


class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TargetFolderRequest(BaseModel):
    target_parent_id: uuid.UUID | None = None


class StorageUsageResponse(BaseModel):
    used_bytes: int
    quota_bytes: int


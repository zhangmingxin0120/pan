import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import asc, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Node, NodeKind, User
from app.schemas.node import (
    BreadcrumbItem,
    FolderCreateRequest,
    NodeListResponse,
    NodeResponse,
    RenameRequest,
    StorageUsageResponse,
    TargetFolderRequest,
)
from app.services import nodes as node_service
from app.services.storage import delete_stored_file, save_upload, storage_path, stored_file_exists

router = APIRouter(prefix="/nodes", tags=["文件"])


@router.get("", response_model=NodeListResponse)
async def list_nodes(
    parent_id: uuid.UUID | None = None,
    search: str | None = Query(default=None, max_length=100),
    sort_by: str = Query(default="updated_at", pattern="^(name|size|updated_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    folder = await node_service.resolve_folder(db, user.id, parent_id)
    filters = [Node.owner_id == user.id, Node.parent_id == folder.id, Node.trashed_at.is_(None)]
    if search:
        filters.append(Node.name.ilike(f"%{search.strip()}%"))
    sort_columns = {"name": func.lower(Node.name), "size": Node.size_bytes, "updated_at": Node.updated_at}
    order = asc(sort_columns[sort_by]) if sort_order == "asc" else desc(sort_columns[sort_by])
    order_by = [case((Node.kind == NodeKind.FOLDER, 0), else_=1), order]
    total = int(await db.scalar(select(func.count(Node.id)).where(*filters)) or 0)
    items = list(
        (
            await db.scalars(
                select(Node)
                .where(*filters)
                .order_by(*order_by)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    path = await node_service.breadcrumbs(db, folder, user.id)
    return NodeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        breadcrumbs=[BreadcrumbItem(id=item.id, name=item.name) for item in path],
        current_folder=folder,
    )


@router.get("/folders", response_model=list[NodeResponse])
async def list_folders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return list(
        (
            await db.scalars(
                select(Node)
                .where(
                    Node.owner_id == user.id,
                    Node.kind == NodeKind.FOLDER,
                    Node.trashed_at.is_(None),
                )
                .order_by(func.lower(Node.name))
            )
        ).all()
    )


@router.post("/folders", response_model=NodeResponse, status_code=201)
async def create_folder(
    payload: FolderCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await node_service.create_folder(db, user, payload.parent_id, payload.name)


@router.post("/upload", response_model=NodeResponse, status_code=201)
async def upload_file(
    parent_id: uuid.UUID | None = Form(default=None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parent = await node_service.resolve_folder(db, user.id, parent_id)
    name = node_service.clean_name(file.filename or "未命名文件")
    await node_service.ensure_name_available(db, user.id, parent.id, name)
    known_size = file.size or 0
    if known_size > settings.max_file_size_bytes:
        raise AppError(413, "FILE_TOO_LARGE", "文件超过单文件大小限制")
    if await node_service.used_bytes(db, user.id) + known_size > user.quota_bytes:
        raise AppError(413, "QUOTA_EXCEEDED", "空间不足，无法上传该文件")
    storage_key, size = await save_upload(file)
    if await node_service.used_bytes(db, user.id) + size > user.quota_bytes:
        delete_stored_file(storage_key)
        raise AppError(413, "QUOTA_EXCEEDED", "空间不足，无法上传该文件")
    node = Node(
        owner_id=user.id,
        parent_id=parent.id,
        kind=NodeKind.FILE,
        name=name,
        size_bytes=size,
        content_type=file.content_type or "application/octet-stream",
        storage_key=storage_key,
    )
    db.add(node)
    try:
        await db.commit()
    except Exception:
        delete_stored_file(storage_key)
        raise
    await db.refresh(node)
    return node


@router.patch("/{node_id}/name", response_model=NodeResponse)
async def rename(
    node_id: uuid.UUID,
    payload: RenameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    node = await node_service.get_owned_node(db, user.id, node_id)
    return await node_service.rename_node(db, user, node, payload.name)


@router.post("/{node_id}/move", response_model=NodeResponse)
async def move(
    node_id: uuid.UUID,
    payload: TargetFolderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    node = await node_service.get_owned_node(db, user.id, node_id)
    return await node_service.move_node(db, user, node, payload.target_parent_id)


@router.post("/{node_id}/copy", response_model=NodeResponse, status_code=201)
async def copy(
    node_id: uuid.UUID,
    payload: TargetFolderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    node = await node_service.get_owned_node(db, user.id, node_id)
    return await node_service.copy_node(db, user, node, payload.target_parent_id)


@router.delete("/{node_id}", status_code=204)
async def remove(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    node = await node_service.get_owned_node(db, user.id, node_id)
    await node_service.trash_node(db, user, node)


def file_response(node: Node, inline: bool = False) -> FileResponse:
    if node.kind != NodeKind.FILE or not stored_file_exists(node.storage_key):
        raise AppError(404, "FILE_NOT_FOUND", "文件内容不存在")
    return FileResponse(
        storage_path(node.storage_key),
        media_type=node.content_type or "application/octet-stream",
        filename=node.name,
        content_disposition_type="inline" if inline else "attachment",
    )


@router.get("/{node_id}/download")
async def download(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return file_response(await node_service.get_owned_node(db, user.id, node_id))


@router.get("/{node_id}/preview")
async def preview(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return file_response(await node_service.get_owned_node(db, user.id, node_id), inline=True)

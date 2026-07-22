import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ApiContext, get_api_context
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Node, NodeKind
from app.schemas.node import (
    BreadcrumbItem,
    FolderCreateRequest,
    NodeListResponse,
    NodeResponse,
    RenameRequest,
    TargetFolderRequest,
)
from app.schemas.integration import FindListResponse
from app.services import nodes as node_service
from app.services.storage import delete_stored_file, save_upload, storage_path, stored_file_exists

router = APIRouter(prefix="/open", tags=["开放 API - 文件管理"])


def require_permission(context: ApiContext, permission: str) -> None:
    allowed = {
        "read": context.application.can_read,
        "write": context.application.can_write,
        "delete": context.application.can_delete,
    }[permission]
    if not allowed:
        raise AppError(403, "API_PERMISSION_DENIED", f"API 应用没有 {permission} 权限")


async def scoped_node(
    db: AsyncSession, context: ApiContext, node_id: uuid.UUID, *, allow_root: bool = True
) -> Node:
    node = await node_service.get_owned_node(db, context.user.id, node_id)
    if not allow_root and node.is_root:
        raise AppError(422, "ROOT_IMMUTABLE", "账号根目录不能修改")
    return node


async def scoped_folder(
    db: AsyncSession, context: ApiContext, folder_id: uuid.UUID | None
) -> Node:
    folder = await node_service.resolve_folder(db, context.user.id, folder_id)
    if folder.kind != NodeKind.FOLDER:
        raise AppError(422, "NOT_A_FOLDER", "目标位置不是文件夹")
    return folder


@router.get("/findlist", response_model=FindListResponse)
async def find_list(
    node_id: uuid.UUID | None = Query(
        default=None, description="查询指定文件或文件夹的 UUID"
    ),
    parent_id: uuid.UUID | None = Query(
        default=None, description="只查询指定文件夹的直接子内容"
    ),
    keyword: str | None = Query(
        default=None, max_length=100, description="在账号全部资源中按名称搜索"
    ),
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    """不传参数返回账号全部有效资源，也可按节点、父目录或名称精确查询。"""
    require_permission(context, "read")
    if node_id and parent_id:
        raise AppError(422, "INVALID_QUERY", "node_id 和 parent_id 不能同时使用")
    filters = [Node.owner_id == context.user.id, Node.trashed_at.is_(None)]
    if node_id:
        filters.append(Node.id == node_id)
    if parent_id:
        parent = await scoped_folder(db, context, parent_id)
        filters.append(Node.parent_id == parent.id)
    if keyword and keyword.strip():
        filters.append(Node.name.ilike(f"%{keyword.strip()}%"))
    items = list(
        (
            await db.scalars(
                select(Node)
                .where(*filters)
                .order_by(
                    case((Node.kind == NodeKind.FOLDER, 0), else_=1),
                    desc(Node.updated_at),
                )
            )
        ).all()
    )
    if node_id and not items:
        raise AppError(404, "NODE_NOT_FOUND", "内容不存在或无权访问")
    return FindListResponse(items=items, total=len(items))


@router.get("/nodes", response_model=NodeListResponse)
async def list_nodes(
    parent_id: uuid.UUID | None = None,
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    require_permission(context, "read")
    folder = await scoped_folder(db, context, parent_id)
    filters = [
        Node.owner_id == context.user.id,
        Node.parent_id == folder.id,
        Node.trashed_at.is_(None),
    ]
    if search and search.strip():
        filters.append(Node.name.ilike(f"%{search.strip()}%"))
    total = int(await db.scalar(select(func.count(Node.id)).where(*filters)) or 0)
    items = list(
        (
            await db.scalars(
                select(Node)
                .where(*filters)
                .order_by(
                    case((Node.kind == NodeKind.FOLDER, 0), else_=1),
                    desc(Node.updated_at),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    path = await node_service.breadcrumbs(db, folder, context.user.id)
    return NodeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        breadcrumbs=[BreadcrumbItem(id=item.id, name=item.name) for item in path],
        current_folder=folder,
    )


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: uuid.UUID,
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    require_permission(context, "read")
    return await scoped_node(db, context, node_id)


@router.post("/folders", response_model=NodeResponse, status_code=201)
async def create_folder(
    payload: FolderCreateRequest,
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    require_permission(context, "write")
    parent = await scoped_folder(db, context, payload.parent_id)
    return await node_service.create_folder(db, context.user, parent.id, payload.name)


@router.post("/upload", response_model=NodeResponse, status_code=201)
async def upload_file(
    parent_id: uuid.UUID | None = Form(default=None),
    file: UploadFile = File(...),
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    require_permission(context, "write")
    parent = await scoped_folder(db, context, parent_id)
    name = node_service.clean_name(file.filename or "未命名文件")
    await node_service.ensure_name_available(db, context.user.id, parent.id, name)
    known_size = file.size or 0
    if known_size > settings.max_file_size_bytes:
        raise AppError(413, "FILE_TOO_LARGE", "文件超过单文件大小限制")
    if await node_service.used_bytes(db, context.user.id) + known_size > context.user.quota_bytes:
        raise AppError(413, "QUOTA_EXCEEDED", "空间不足，无法上传该文件")
    key, size = await save_upload(file)
    if await node_service.used_bytes(db, context.user.id) + size > context.user.quota_bytes:
        delete_stored_file(key)
        raise AppError(413, "QUOTA_EXCEEDED", "空间不足，无法上传该文件")
    node = Node(
        owner_id=context.user.id,
        parent_id=parent.id,
        kind=NodeKind.FILE,
        name=name,
        size_bytes=size,
        content_type=file.content_type or "application/octet-stream",
        storage_key=key,
    )
    db.add(node)
    try:
        await db.commit()
    except Exception:
        delete_stored_file(key)
        raise
    await db.refresh(node)
    context.upload_bytes = size
    return node


@router.patch("/nodes/{node_id}/name", response_model=NodeResponse)
async def rename_node(
    node_id: uuid.UUID,
    payload: RenameRequest,
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    require_permission(context, "write")
    node = await scoped_node(db, context, node_id, allow_root=False)
    return await node_service.rename_node(db, context.user, node, payload.name)


@router.post("/nodes/{node_id}/move", response_model=NodeResponse)
async def move_node(
    node_id: uuid.UUID,
    payload: TargetFolderRequest,
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    require_permission(context, "write")
    node = await scoped_node(db, context, node_id, allow_root=False)
    target = await scoped_folder(db, context, payload.target_parent_id)
    return await node_service.move_node(db, context.user, node, target.id)


@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(
    node_id: uuid.UUID,
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    require_permission(context, "delete")
    node = await scoped_node(db, context, node_id, allow_root=False)
    await node_service.trash_node(db, context.user, node)


@router.get("/nodes/{node_id}/download")
async def download_file(
    node_id: uuid.UUID,
    context: ApiContext = Depends(get_api_context),
    db: AsyncSession = Depends(get_db),
):
    require_permission(context, "read")
    node = await scoped_node(db, context, node_id)
    if node.kind != NodeKind.FILE or not stored_file_exists(node.storage_key):
        raise AppError(404, "FILE_NOT_FOUND", "文件内容不存在")
    context.download_bytes = node.size_bytes
    return FileResponse(
        storage_path(node.storage_key),
        media_type=node.content_type or "application/octet-stream",
        filename=node.name,
    )

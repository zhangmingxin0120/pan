import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Node, NodeKind, Share, User
from app.schemas.node import BreadcrumbItem
from app.schemas.share import (
    PublicShareResponse,
    ShareCreateRequest,
    ShareListResponse,
    ShareResponse,
)
from app.services import nodes as node_service
from app.services.storage import storage_path, stored_file_exists

router = APIRouter(prefix="/shares", tags=["分享"])
public_router = APIRouter(prefix="/public/shares", tags=["公开分享"])


def utc_now_for(value: datetime) -> datetime:
    now = datetime.now(UTC)
    return now if value.tzinfo is not None else now.replace(tzinfo=None)


def share_response(share: Share, node: Node) -> ShareResponse:
    return ShareResponse(
        id=share.id,
        token=share.token,
        node=node,
        expires_at=share.expires_at,
        revoked_at=share.revoked_at,
        created_at=share.created_at,
        is_active=share.revoked_at is None
        and (share.expires_at is None or share.expires_at > utc_now_for(share.expires_at))
        and node.trashed_at is None,
    )


@router.post("", response_model=ShareResponse, status_code=201)
async def create_share(
    payload: ShareCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    node = await node_service.get_owned_node(db, user.id, payload.node_id)
    share = Share(
        owner_id=user.id,
        node_id=node.id,
        token=secrets.token_urlsafe(24),
        expires_at=(
            datetime.now(UTC) + timedelta(days=payload.expires_in_days)
            if payload.expires_in_days is not None
            else None
        ),
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    return share_response(share, node)


@router.get("", response_model=ShareListResponse)
async def list_shares(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = int(await db.scalar(select(func.count(Share.id)).where(Share.owner_id == user.id)) or 0)
    rows = (
        await db.execute(
            select(Share, Node)
            .join(Node, Node.id == Share.node_id)
            .where(Share.owner_id == user.id)
            .order_by(desc(Share.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ShareListResponse(
        items=[share_response(share, node) for share, node in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{share_id}", status_code=204)
async def revoke_share(
    share_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    share = await db.scalar(select(Share).where(Share.id == share_id, Share.owner_id == user.id))
    if not share:
        raise AppError(404, "SHARE_NOT_FOUND", "分享不存在")
    share.revoked_at = datetime.now(UTC)
    await db.commit()


@router.delete("/{share_id}/record", status_code=204)
async def delete_share_record(
    share_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    share = await db.scalar(select(Share).where(Share.id == share_id, Share.owner_id == user.id))
    if not share:
        raise AppError(404, "SHARE_NOT_FOUND", "分享不存在")
    node = await db.get(Node, share.node_id)
    is_expired = share.expires_at is not None and share.expires_at <= utc_now_for(share.expires_at)
    if share.revoked_at is None and not is_expired and node and node.trashed_at is None:
        raise AppError(409, "SHARE_STILL_ACTIVE", "请先取消分享，再删除记录")
    await db.delete(share)
    await db.commit()


async def get_active_share(db: AsyncSession, token: str) -> tuple[Share, Node, User]:
    row = (
        await db.execute(
            select(Share, Node, User)
            .join(Node, Node.id == Share.node_id)
            .join(User, User.id == Share.owner_id)
            .where(Share.token == token)
        )
    ).first()
    if not row:
        raise AppError(404, "SHARE_NOT_FOUND", "分享不存在或已失效")
    share, root, owner = row
    if (
        share.revoked_at
        or (share.expires_at is not None and share.expires_at <= utc_now_for(share.expires_at))
        or root.trashed_at
    ):
        raise AppError(410, "SHARE_EXPIRED", "分享不存在或已失效")
    return share, root, owner


async def public_node(
    db: AsyncSession, root: Node, node_id: uuid.UUID | None, *, require_file: bool = False
) -> Node:
    if node_id is None:
        node = root
    else:
        node = await db.scalar(
            select(Node).where(Node.id == node_id, Node.owner_id == root.owner_id, Node.trashed_at.is_(None))
        )
        if not node:
            raise AppError(404, "NODE_NOT_FOUND", "分享内容不存在")
        nodes = await node_service.all_owner_nodes(db, root.owner_id)
        if node.id not in node_service.descendant_ids(nodes, root.id):
            raise AppError(404, "NODE_NOT_FOUND", "分享内容不存在")
    if require_file and node.kind != NodeKind.FILE:
        raise AppError(422, "NOT_A_FILE", "该内容不是文件")
    return node


@public_router.get("/{token}", response_model=PublicShareResponse)
async def view_share(token: str, parent_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    share, root, owner = await get_active_share(db, token)
    current = await public_node(db, root, parent_id)
    if current.kind == NodeKind.FILE:
        items: list[Node] = []
        current_folder = None
        path = [root]
    else:
        items = list(
            (
                await db.scalars(
                    select(Node)
                    .where(Node.parent_id == current.id, Node.trashed_at.is_(None))
                    .order_by(case((Node.kind == NodeKind.FOLDER, 0), else_=1), func.lower(Node.name))
                )
            ).all()
        )
        current_folder = current
        full_path = await node_service.breadcrumbs(db, current, owner.id)
        root_index = next(index for index, item in enumerate(full_path) if item.id == root.id)
        path = full_path[root_index:]
    return PublicShareResponse(
        token=token,
        root=root,
        current_folder=current_folder,
        breadcrumbs=[BreadcrumbItem(id=item.id, name=item.name) for item in path],
        items=items,
        expires_at=share.expires_at,
        owner_name=owner.name,
    )


@public_router.get("/{token}/nodes/{node_id}/download")
async def public_download(token: str, node_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    _, root, _ = await get_active_share(db, token)
    node = await public_node(db, root, node_id, require_file=True)
    if not stored_file_exists(node.storage_key):
        raise AppError(404, "FILE_NOT_FOUND", "文件内容不存在")
    return FileResponse(
        storage_path(node.storage_key),
        media_type=node.content_type or "application/octet-stream",
        filename=node.name,
    )


@public_router.get("/{token}/nodes/{node_id}/preview")
async def public_preview(token: str, node_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    _, root, _ = await get_active_share(db, token)
    node = await public_node(db, root, node_id, require_file=True)
    if not stored_file_exists(node.storage_key):
        raise AppError(404, "FILE_NOT_FOUND", "文件内容不存在")
    return FileResponse(
        storage_path(node.storage_key),
        media_type=node.content_type or "application/octet-stream",
        filename=node.name,
        content_disposition_type="inline",
    )

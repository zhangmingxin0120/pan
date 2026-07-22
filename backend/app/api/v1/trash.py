import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Node, User
from app.schemas.node import NodeResponse
from app.services import nodes as node_service

router = APIRouter(prefix="/trash", tags=["回收站"])


@router.get("", response_model=list[NodeResponse])
async def list_trash(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    nodes = await node_service.all_owner_nodes(db, user.id)
    by_id = {node.id: node for node in nodes}
    roots = [
        node
        for node in nodes
        if node.trashed_at is not None
        and (node.parent_id is None or by_id.get(node.parent_id) is None or by_id[node.parent_id].trashed_at is None)
    ]
    roots.sort(key=lambda node: node.trashed_at, reverse=True)
    start = (page - 1) * page_size
    return roots[start : start + page_size]


@router.post("/{node_id}/restore", response_model=NodeResponse)
async def restore(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    node = await node_service.get_owned_node(db, user.id, node_id, include_trashed=True)
    return await node_service.restore_node(db, user, node)


@router.delete("/{node_id}", status_code=204)
async def permanent_delete(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    node = await node_service.get_owned_node(db, user.id, node_id, include_trashed=True)
    await node_service.permanently_delete_node(db, user, node)


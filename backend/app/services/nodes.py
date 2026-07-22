import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Node, NodeKind, User
from app.services.storage import copy_stored_file, delete_stored_file

INVALID_NAME = re.compile(r"[\\/\x00-\x1f\x7f]")


def clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or cleaned in {".", ".."} or INVALID_NAME.search(cleaned):
        raise AppError(422, "INVALID_NAME", "名称不能为空，且不能包含 /、\\ 或控制字符")
    return cleaned


async def get_root(db: AsyncSession, owner_id: uuid.UUID) -> Node:
    root = await db.scalar(select(Node).where(Node.owner_id == owner_id, Node.is_root.is_(True)))
    if not root:
        raise AppError(500, "ROOT_MISSING", "文件空间初始化失败")
    return root


async def get_owned_node(
    db: AsyncSession,
    owner_id: uuid.UUID,
    node_id: uuid.UUID,
    *,
    include_trashed: bool = False,
) -> Node:
    query = select(Node).where(Node.id == node_id, Node.owner_id == owner_id)
    if not include_trashed:
        query = query.where(Node.trashed_at.is_(None))
    node = await db.scalar(query)
    if not node:
        raise AppError(404, "NODE_NOT_FOUND", "内容不存在或无权访问")
    return node


async def resolve_folder(
    db: AsyncSession, owner_id: uuid.UUID, folder_id: uuid.UUID | None
) -> Node:
    folder = await get_root(db, owner_id) if folder_id is None else await get_owned_node(db, owner_id, folder_id)
    if folder.kind != NodeKind.FOLDER:
        raise AppError(422, "NOT_A_FOLDER", "目标位置不是文件夹")
    return folder


async def ensure_name_available(
    db: AsyncSession,
    owner_id: uuid.UUID,
    parent_id: uuid.UUID,
    name: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    query = select(Node.id).where(
        Node.owner_id == owner_id,
        Node.parent_id == parent_id,
        Node.trashed_at.is_(None),
        func.lower(Node.name) == name.lower(),
    )
    if exclude_id:
        query = query.where(Node.id != exclude_id)
    if await db.scalar(query):
        raise AppError(409, "NAME_CONFLICT", "当前文件夹中已存在同名内容")


async def breadcrumbs(db: AsyncSession, node: Node, owner_id: uuid.UUID) -> list[Node]:
    result = [node]
    current = node
    for _ in range(50):
        if current.parent_id is None:
            break
        current = await get_owned_node(db, owner_id, current.parent_id)
        result.append(current)
    return list(reversed(result))


async def all_owner_nodes(db: AsyncSession, owner_id: uuid.UUID) -> list[Node]:
    return list((await db.scalars(select(Node).where(Node.owner_id == owner_id))).all())


def descendant_ids(nodes: list[Node], root_id: uuid.UUID, include_root: bool = True) -> set[uuid.UUID]:
    children: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for node in nodes:
        if node.parent_id:
            children[node.parent_id].append(node.id)
    found = {root_id} if include_root else set()
    stack = list(children[root_id])
    while stack:
        item = stack.pop()
        if item in found:
            continue
        found.add(item)
        stack.extend(children[item])
    return found


async def used_bytes(db: AsyncSession, owner_id: uuid.UUID) -> int:
    value = await db.scalar(
        select(func.coalesce(func.sum(Node.size_bytes), 0)).where(
            Node.owner_id == owner_id, Node.kind == NodeKind.FILE
        )
    )
    return int(value or 0)


async def create_folder(db: AsyncSession, user: User, parent_id: uuid.UUID | None, name: str) -> Node:
    parent = await resolve_folder(db, user.id, parent_id)
    clean = clean_name(name)
    await ensure_name_available(db, user.id, parent.id, clean)
    node = Node(owner_id=user.id, parent_id=parent.id, kind=NodeKind.FOLDER, name=clean)
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


async def rename_node(db: AsyncSession, user: User, node: Node, name: str) -> Node:
    if node.is_root:
        raise AppError(422, "ROOT_IMMUTABLE", "根目录不能重命名")
    clean = clean_name(name)
    await ensure_name_available(db, user.id, node.parent_id, clean, node.id)
    node.name = clean
    await db.commit()
    await db.refresh(node)
    return node


async def move_node(db: AsyncSession, user: User, node: Node, target_parent_id: uuid.UUID | None) -> Node:
    if node.is_root:
        raise AppError(422, "ROOT_IMMUTABLE", "根目录不能移动")
    target = await resolve_folder(db, user.id, target_parent_id)
    if node.id == target.id:
        raise AppError(422, "INVALID_MOVE", "文件夹不能移动到自身")
    if node.kind == NodeKind.FOLDER:
        nodes = await all_owner_nodes(db, user.id)
        if target.id in descendant_ids(nodes, node.id):
            raise AppError(422, "INVALID_MOVE", "文件夹不能移动到自己的子文件夹中")
    await ensure_name_available(db, user.id, target.id, node.name, node.id)
    node.parent_id = target.id
    await db.commit()
    await db.refresh(node)
    return node


async def copy_node(db: AsyncSession, user: User, source: Node, target_parent_id: uuid.UUID | None) -> Node:
    target = await resolve_folder(db, user.id, target_parent_id)
    await ensure_name_available(db, user.id, target.id, source.name)
    all_nodes = await all_owner_nodes(db, user.id)
    by_parent: dict[uuid.UUID, list[Node]] = defaultdict(list)
    for item in all_nodes:
        if item.parent_id and item.trashed_at is None:
            by_parent[item.parent_id].append(item)
    copied_ids = descendant_ids(all_nodes, source.id)
    copy_size = sum(
        item.size_bytes for item in all_nodes if item.id in copied_ids and item.kind == NodeKind.FILE
    )
    if await used_bytes(db, user.id) + copy_size > user.quota_bytes:
        raise AppError(413, "QUOTA_EXCEEDED", "空间不足，无法复制这些内容")

    async def clone(item: Node, parent: Node) -> Node:
        key = copy_stored_file(item.storage_key) if item.kind == NodeKind.FILE and item.storage_key else None
        copied = Node(
            owner_id=user.id,
            parent_id=parent.id,
            kind=item.kind,
            name=item.name,
            size_bytes=item.size_bytes,
            content_type=item.content_type,
            storage_key=key,
        )
        db.add(copied)
        await db.flush()
        for child in by_parent[item.id]:
            await clone(child, copied)
        return copied

    copied = await clone(source, target)
    await db.commit()
    await db.refresh(copied)
    return copied


async def trash_node(db: AsyncSession, user: User, node: Node) -> None:
    if node.is_root:
        raise AppError(422, "ROOT_IMMUTABLE", "根目录不能删除")
    nodes = await all_owner_nodes(db, user.id)
    ids = descendant_ids(nodes, node.id)
    now = datetime.now(UTC)
    for item in nodes:
        if item.id in ids:
            if item.id == node.id:
                item.original_parent_id = item.parent_id
            item.trashed_at = now
    await db.commit()


async def available_restore_name(
    db: AsyncSession, owner_id: uuid.UUID, parent_id: uuid.UUID, original: str
) -> str:
    candidate = original
    index = 1
    while await db.scalar(
        select(Node.id).where(
            Node.owner_id == owner_id,
            Node.parent_id == parent_id,
            Node.trashed_at.is_(None),
            func.lower(Node.name) == candidate.lower(),
        )
    ):
        dot = original.rfind(".")
        if dot > 0:
            candidate = f"{original[:dot]}（恢复 {index}）{original[dot:]}"
        else:
            candidate = f"{original}（恢复 {index}）"
        index += 1
    return candidate


async def restore_node(db: AsyncSession, user: User, node: Node) -> Node:
    if node.trashed_at is None:
        raise AppError(409, "NOT_TRASHED", "内容不在回收站")
    nodes = await all_owner_nodes(db, user.id)
    node_by_id = {item.id: item for item in nodes}
    target = node_by_id.get(node.original_parent_id) if node.original_parent_id else None
    if not target or target.trashed_at is not None or target.kind != NodeKind.FOLDER:
        target = await get_root(db, user.id)
    node.name = await available_restore_name(db, user.id, target.id, node.name)
    node.parent_id = target.id
    node.original_parent_id = None
    for item in nodes:
        if item.id in descendant_ids(nodes, node.id):
            item.trashed_at = None
    await db.commit()
    await db.refresh(node)
    return node


async def permanently_delete_node(db: AsyncSession, user: User, node: Node) -> None:
    if node.trashed_at is None:
        raise AppError(409, "NOT_TRASHED", "只有回收站内容可以永久删除")
    nodes = await all_owner_nodes(db, user.id)
    ids = descendant_ids(nodes, node.id)
    for item in nodes:
        if item.id in ids and item.kind == NodeKind.FILE:
            delete_stored_file(item.storage_key)
    await db.delete(node)
    await db.commit()


async def empty_trash(db: AsyncSession, user: User) -> int:
    nodes = await all_owner_nodes(db, user.id)
    trashed = [item for item in nodes if item.trashed_at is not None]
    if not trashed:
        return 0
    trashed_ids = {item.id for item in trashed}
    for item in trashed:
        if item.kind == NodeKind.FILE:
            delete_stored_file(item.storage_key)
    await db.execute(
        delete(Node).where(Node.id.in_(trashed_ids)).execution_options(synchronize_session=False)
    )
    await db.commit()
    return len(trashed)

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.models import Node, NodeKind, User
from app.schemas.auth import AdminLoginRequest, TokenResponse
from app.schemas.admin import (
    AdminOverviewResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
)

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.post("/login", response_model=TokenResponse)
async def admin_login(payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    username = payload.username.strip().lower()
    user = await db.scalar(
        select(User).where(func.lower(User.username) == username, User.is_admin.is_(True))
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(401, "INVALID_ADMIN_CREDENTIALS", "管理员账号或密码不正确")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "管理员账号已停用")
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.token_version), user=user
    )


@router.get("/overview", response_model=AdminOverviewResponse)
async def overview(_: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    regular_user = User.is_admin.is_(False)
    return AdminOverviewResponse(
        user_count=int(await db.scalar(select(func.count(User.id)).where(regular_user)) or 0),
        active_user_count=int(
            await db.scalar(select(func.count(User.id)).where(regular_user, User.is_active.is_(True))) or 0
        ),
        file_count=int(await db.scalar(select(func.count(Node.id)).where(Node.kind == NodeKind.FILE)) or 0),
        storage_bytes=int(
            await db.scalar(
                select(func.coalesce(func.sum(Node.size_bytes), 0)).where(Node.kind == NodeKind.FILE)
            )
            or 0
        ),
    )


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    search: str | None = Query(default=None, max_length=100),
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [User.is_admin.is_(False)]
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append((User.email.ilike(term)) | (User.name.ilike(term)))
    users = list((await db.scalars(select(User).where(*filters).order_by(User.created_at.desc()))).all())
    usage_rows = (
        await db.execute(
            select(Node.owner_id, func.coalesce(func.sum(Node.size_bytes), 0))
            .where(Node.kind == NodeKind.FILE)
            .group_by(Node.owner_id)
        )
    ).all()
    usage = {owner_id: int(size) for owner_id, size in usage_rows}
    return AdminUserListResponse(
        items=[
            AdminUserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                is_active=user.is_active,
                quota_bytes=user.quota_bytes,
                used_bytes=usage.get(user.id, 0),
                created_at=user.created_at,
            )
            for user in users
        ],
        total=len(users),
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.id == user_id, User.is_admin.is_(False)))
    if not user:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")
    if payload.is_active is not None and payload.is_active != user.is_active:
        user.is_active = payload.is_active
        user.token_version += 1
    if payload.quota_bytes is not None:
        user.quota_bytes = payload.quota_bytes
    await db.commit()
    await db.refresh(user)
    used = int(
        await db.scalar(
            select(func.coalesce(func.sum(Node.size_bytes), 0)).where(
                Node.owner_id == user.id, Node.kind == NodeKind.FILE
            )
        )
        or 0
    )
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        quota_bytes=user.quota_bytes,
        used_bytes=used,
        created_at=user.created_at,
    )

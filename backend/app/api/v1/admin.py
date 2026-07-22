import secrets
import shutil
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Node, NodeKind, User
from app.schemas.auth import AdminLoginRequest, TokenResponse
from app.schemas.admin import (
    AdminPasswordResetRequest,
    AdminPasswordResetResponse,
    AdminOverviewResponse,
    AdminSettingsResponse,
    AdminSettingsUpdateRequest,
    AdminUserCreateRequest,
    AdminUserCreateResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from app.services.storage import storage_root
from app.services.system_settings import get_system_settings

router = APIRouter(prefix="/admin", tags=["管理员"])


def temporary_password() -> str:
    return secrets.token_urlsafe(12)


def user_response(user: User, used_bytes: int = 0) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        quota_bytes=user.quota_bytes,
        used_bytes=used_bytes,
        created_at=user.created_at,
    )


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
    disk = shutil.disk_usage(storage_root())
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
        disk_total_bytes=disk.total,
        disk_free_bytes=disk.free,
    )


@router.get("/settings", response_model=AdminSettingsResponse)
async def get_settings(
    _: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)
):
    system_settings = await get_system_settings(db)
    return AdminSettingsResponse(registration_enabled=system_settings.registration_enabled)


@router.patch("/settings", response_model=AdminSettingsResponse)
async def update_settings(
    payload: AdminSettingsUpdateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    system_settings = await get_system_settings(db)
    system_settings.registration_enabled = payload.registration_enabled
    await db.commit()
    return AdminSettingsResponse(registration_enabled=system_settings.registration_enabled)


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
            user_response(user, usage.get(user.id, 0))
            for user in users
        ],
        total=len(users),
    )


@router.post("/users", response_model=AdminUserCreateResponse, status_code=201)
async def create_user(
    payload: AdminUserCreateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    email = payload.email.lower()
    name = payload.name.strip()
    if not name:
        raise AppError(422, "INVALID_NAME", "显示名称不能为空")
    if await db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise AppError(409, "EMAIL_EXISTS", "该邮箱已注册")
    password = temporary_password()
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),
        quota_bytes=(
            payload.quota_bytes
            if payload.quota_bytes is not None
            else settings.default_quota_bytes
        ),
        must_change_password=True,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    db.add(
        Node(
            owner_id=user.id,
            parent_id=None,
            kind=NodeKind.FOLDER,
            name="我的文件",
            is_root=True,
        )
    )
    await db.commit()
    await db.refresh(user)
    return AdminUserCreateResponse(user=user_response(user), temporary_password=password)


@router.post("/users/{user_id}/reset-password", response_model=AdminPasswordResetResponse)
async def reset_user_password(
    user_id: uuid.UUID,
    payload: AdminPasswordResetRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.id == user_id, User.is_admin.is_(False)))
    if not user:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")
    user.password_hash = hash_password(payload.password)
    user.must_change_password = True
    user.token_version += 1
    await db.commit()
    return AdminPasswordResetResponse(temporary_password=payload.password)


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
    return user_response(user, used)

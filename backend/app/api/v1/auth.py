from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_user
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Node, NodeKind, User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.lower()
    name = payload.name.strip()
    if not name:
        raise AppError(422, "INVALID_NAME", "显示名称不能为空")
    if await db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise AppError(409, "EMAIL_EXISTS", "该邮箱已注册")
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(payload.password),
        quota_bytes=settings.default_quota_bytes,
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
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.token_version), user=user
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(
        select(User).where(func.lower(User.email) == payload.email.lower(), User.is_admin.is_(False))
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "邮箱或密码不正确")
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.token_version), user=user
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_authenticated_user)):
    return user


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise AppError(422, "CURRENT_PASSWORD_INVALID", "当前密码不正确")
    if verify_password(payload.new_password, user.password_hash):
        raise AppError(422, "PASSWORD_UNCHANGED", "新密码不能与当前密码相同")
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    user.must_change_password = False
    await db.commit()
    await db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.token_version), user=user
    )

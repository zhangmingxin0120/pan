import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models import User

bearer = HTTPBearer(auto_error=False)


async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(401, "NOT_AUTHENTICATED", "请先登录")
    token_data = decode_access_token(credentials.credentials)
    if not token_data:
        raise AppError(401, "INVALID_TOKEN", "登录状态已失效，请重新登录")
    subject, token_version = token_data
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise AppError(401, "INVALID_TOKEN", "登录状态已失效，请重新登录") from exc
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user or user.token_version != token_version:
        raise AppError(401, "INVALID_TOKEN", "登录状态已失效，请重新登录")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "账号已被管理员停用")
    return user


async def get_current_user(user: User = Depends(get_authenticated_user)) -> User:
    if user.must_change_password:
        raise AppError(403, "PASSWORD_CHANGE_REQUIRED", "首次登录必须先修改密码")
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise AppError(403, "ADMIN_REQUIRED", "需要管理员权限")
    return user

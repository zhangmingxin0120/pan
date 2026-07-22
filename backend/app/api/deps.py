import hmac
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models import ApiApplication, User
from app.services.api_keys import api_key_hash, api_key_prefix

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


@dataclass
class ApiContext:
    application: ApiApplication
    user: User
    upload_bytes: int = 0
    download_bytes: int = 0


async def get_api_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> AsyncIterator[ApiContext]:
    if credentials is None:
        raise AppError(401, "API_KEY_REQUIRED", "请提供 API Key")
    raw_key = credentials.credentials
    prefix = api_key_prefix(raw_key)
    if not prefix:
        raise AppError(401, "INVALID_API_KEY", "API Key 无效")
    application = await db.scalar(
        select(ApiApplication).where(ApiApplication.key_prefix == prefix)
    )
    if not application or not hmac.compare_digest(
        application.key_hash, api_key_hash(raw_key)
    ):
        raise AppError(401, "INVALID_API_KEY", "API Key 无效")
    user = await db.get(User, application.user_id)
    if not application.is_active:
        raise AppError(403, "API_APPLICATION_DISABLED", "API 应用已停用")
    if not user or not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "关联账号已停用")
    context = ApiContext(application=application, user=user)
    application_id = application.id
    failed = False
    try:
        yield context
    except Exception:
        failed = True
        await db.rollback()
        raise
    finally:
        await db.execute(
            update(ApiApplication)
            .where(ApiApplication.id == application_id)
            .values(
                request_count=ApiApplication.request_count + 1,
                failed_request_count=ApiApplication.failed_request_count + int(failed),
                upload_bytes=ApiApplication.upload_bytes + context.upload_bytes,
                download_bytes=ApiApplication.download_bytes + context.download_bytes,
                last_used_at=datetime.now(UTC),
            )
        )
        await db.commit()

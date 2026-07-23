import hmac
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.config import settings
from app.core.security import decode_access_token, verify_csrf_token
from app.models import ApiApplication, User
from app.services.api_keys import api_key_hash, api_key_prefix

bearer = HTTPBearer(auto_error=False)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def validate_cookie_csrf(
    request: Request, subject: str, token_version: int
) -> None:
    if request.method.upper() in SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin:
        origin_host = urlsplit(origin).netloc.lower()
        request_host = request.headers.get("x-forwarded-host", request.headers.get("host", "")).lower()
        trusted_origins = {item.rstrip("/") for item in settings.cors_origin_list}
        if not origin_host or (
            origin_host != request_host and origin.rstrip("/") not in trusted_origins
        ):
            raise AppError(403, "CSRF_ORIGIN_MISMATCH", "请求来源校验失败，请刷新页面后重试")
    cookie_token = request.cookies.get(settings.csrf_cookie_name, "")
    header_token = request.headers.get("x-csrf-token", "")
    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
        or not verify_csrf_token(cookie_token, subject, token_version)
    ):
        raise AppError(403, "CSRF_TOKEN_INVALID", "安全校验失败，请刷新页面后重试")


async def get_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    using_cookie = credentials is None
    token = (
        credentials.credentials
        if credentials is not None
        else request.cookies.get(settings.session_cookie_name)
    )
    if not token:
        raise AppError(401, "NOT_AUTHENTICATED", "请先登录")
    token_data = decode_access_token(token)
    if not token_data:
        raise AppError(401, "INVALID_TOKEN", "登录状态已失效，请重新登录")
    subject, token_version = token_data
    if using_cookie:
        validate_cookie_csrf(request, subject, token_version)
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

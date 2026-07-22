import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import ApiApplication, Node, NodeKind, User
from app.schemas.integration import (
    AdminFolderOption,
    ApiApplicationCreateRequest,
    ApiApplicationListResponse,
    ApiApplicationResponse,
    ApiApplicationSecretResponse,
    ApiApplicationUpdateRequest,
    ApiKeyRotateResponse,
)
from app.services.api_keys import generate_api_key

router = APIRouter(prefix="/admin/integrations", tags=["管理员 - 开放 API"])


def folder_paths(nodes: list[Node]) -> dict[uuid.UUID, str]:
    by_id = {node.id: node for node in nodes}
    result: dict[uuid.UUID, str] = {}
    for node in nodes:
        if node.kind != NodeKind.FOLDER or node.trashed_at is not None:
            continue
        parts: list[str] = []
        current = node
        for _ in range(50):
            if current.is_root:
                break
            parts.append(current.name)
            if not current.parent_id or current.parent_id not in by_id:
                break
            current = by_id[current.parent_id]
        result[node.id] = "/" + "/".join(reversed(parts))
    return result


async def application_response(
    db: AsyncSession, application: ApiApplication
) -> ApiApplicationResponse:
    user = await db.get(User, application.user_id)
    nodes = list(
        (await db.scalars(select(Node).where(Node.owner_id == application.user_id))).all()
    )
    paths = folder_paths(nodes)
    return ApiApplicationResponse(
        id=application.id,
        name=application.name,
        user_id=application.user_id,
        user_email=user.email if user else "账号已删除",
        root_node_id=application.root_node_id,
        root_path=paths.get(application.root_node_id, "授权目录不可用"),
        key_prefix=f"pan_{application.key_prefix}_…",
        can_read=application.can_read,
        can_write=application.can_write,
        can_delete=application.can_delete,
        is_active=application.is_active,
        request_count=application.request_count,
        failed_request_count=application.failed_request_count,
        upload_bytes=application.upload_bytes,
        download_bytes=application.download_bytes,
        last_used_at=application.last_used_at,
        created_at=application.created_at,
    )


async def get_application(db: AsyncSession, application_id: uuid.UUID) -> ApiApplication:
    application = await db.get(ApiApplication, application_id)
    if not application:
        raise AppError(404, "API_APPLICATION_NOT_FOUND", "API 应用不存在")
    return application


@router.get("/users/{user_id}/folders", response_model=list[AdminFolderOption])
async def list_user_folders(
    user_id: uuid.UUID,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.id == user_id, User.is_admin.is_(False)))
    if not user:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")
    nodes = list((await db.scalars(select(Node).where(Node.owner_id == user_id))).all())
    paths = folder_paths(nodes)
    return [
        AdminFolderOption(id=node_id, path=path)
        for node_id, path in sorted(paths.items(), key=lambda item: item[1].lower())
    ]


@router.get("", response_model=ApiApplicationListResponse)
async def list_applications(
    _: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)
):
    applications = list(
        (await db.scalars(select(ApiApplication).order_by(ApiApplication.created_at.desc()))).all()
    )
    return ApiApplicationListResponse(
        items=[await application_response(db, item) for item in applications],
        total=len(applications),
    )


@router.post("", response_model=ApiApplicationSecretResponse, status_code=201)
async def create_application(
    payload: ApiApplicationCreateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(
        select(User).where(User.id == payload.user_id, User.is_admin.is_(False))
    )
    if not user:
        raise AppError(404, "USER_NOT_FOUND", "用户不存在")
    if not user.is_active:
        raise AppError(422, "ACCOUNT_DISABLED", "不能为已停用账号创建 API 应用")
    root = await db.scalar(
        select(Node).where(
            Node.id == payload.root_node_id,
            Node.owner_id == user.id,
            Node.kind == NodeKind.FOLDER,
            Node.trashed_at.is_(None),
        )
    )
    if not root:
        raise AppError(422, "INVALID_API_ROOT", "请选择该账号下的有效文件夹")
    name = payload.name.strip()
    if not name:
        raise AppError(422, "INVALID_NAME", "应用名称不能为空")
    api_key, prefix, key_hash = generate_api_key()
    application = ApiApplication(
        name=name,
        user_id=user.id,
        root_node_id=root.id,
        key_prefix=prefix,
        key_hash=key_hash,
        can_read=payload.can_read,
        can_write=payload.can_write,
        can_delete=payload.can_delete,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return ApiApplicationSecretResponse(
        application=await application_response(db, application), api_key=api_key
    )


@router.patch("/{application_id}", response_model=ApiApplicationResponse)
async def update_application(
    application_id: uuid.UUID,
    payload: ApiApplicationUpdateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    application = await get_application(db, application_id)
    application.is_active = payload.is_active
    await db.commit()
    await db.refresh(application)
    return await application_response(db, application)


@router.post("/{application_id}/rotate-key", response_model=ApiKeyRotateResponse)
async def rotate_key(
    application_id: uuid.UUID,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    application = await get_application(db, application_id)
    api_key, prefix, key_hash = generate_api_key()
    application.key_prefix = prefix
    application.key_hash = key_hash
    await db.commit()
    return ApiKeyRotateResponse(api_key=api_key)

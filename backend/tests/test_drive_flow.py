from pathlib import Path
import uuid

from httpx import AsyncClient

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models import Node, User
from app.services.storage_migration import migrate_legacy_storage_layout


def auth_header(response, token_version: int = 0) -> dict[str, str]:
    token = create_access_token(response.json()["user"]["id"], token_version)
    return {"Authorization": f"Bearer {token}"}


async def test_http_only_cookie_session_and_csrf(client: AsyncClient):
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "cookie@example.com", "name": "Cookie", "password": "password123"},
    )
    assert registered.status_code == 201
    assert "access_token" not in registered.json()
    cookie_headers = registered.headers.get_list("set-cookie")
    session_header = next(
        value for value in cookie_headers if value.startswith(f"{settings.session_cookie_name}=")
    )
    csrf_header = next(
        value for value in cookie_headers if value.startswith(f"{settings.csrf_cookie_name}=")
    )
    assert "HttpOnly" in session_header
    assert "SameSite=lax" in session_header
    assert "HttpOnly" not in csrf_header

    assert (await client.get("/api/v1/auth/me")).status_code == 200
    missing_csrf = await client.post(
        "/api/v1/nodes/folders", json={"name": "不应创建"}
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["code"] == "CSRF_TOKEN_INVALID"

    csrf_token = client.cookies.get(settings.csrf_cookie_name)
    cross_origin = await client.post(
        "/api/v1/nodes/folders",
        json={"name": "跨站请求"},
        headers={"X-CSRF-Token": csrf_token, "Origin": "https://evil.example"},
    )
    assert cross_origin.status_code == 403
    assert cross_origin.json()["code"] == "CSRF_ORIGIN_MISMATCH"
    created = await client.post(
        "/api/v1/nodes/folders",
        json={"name": "安全请求"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201

    assert (await client.post("/api/v1/auth/logout")).status_code == 204
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_file_lifecycle_and_share(
    client: AsyncClient, auth_headers: dict[str, str], session_factory
):
    usage_response = await client.get("/api/v1/storage/usage", headers=auth_headers)
    assert usage_response.status_code == 200
    assert usage_response.json()["quota_bytes"] == 5 * 1024 * 1024 * 1024

    root_response = await client.get("/api/v1/nodes", headers=auth_headers)
    assert root_response.status_code == 200
    root_id = root_response.json()["current_folder"]["id"]

    folder_response = await client.post(
        "/api/v1/nodes/folders",
        json={"parent_id": root_id, "name": "资料"},
        headers=auth_headers,
    )
    assert folder_response.status_code == 201
    folder_id = folder_response.json()["id"]

    duplicate_response = await client.post(
        "/api/v1/nodes/folders",
        json={"parent_id": root_id, "name": "资料"},
        headers=auth_headers,
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["code"] == "NAME_CONFLICT"

    upload_response = await client.post(
        "/api/v1/nodes/upload",
        data={"parent_id": folder_id},
        files={"file": ("readme.txt", b"hello pan", "text/plain")},
        headers=auth_headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]
    async with session_factory() as db:
        stored_node = await db.get(Node, uuid.UUID(file_id))
        assert stored_node is not None and stored_node.storage_key is not None
        key_parts = stored_node.storage_key.split("/")
        assert len(key_parts) == 5
        assert key_parts[3] == key_parts[4][:2]
        assert (Path(settings.storage_path).joinpath(*key_parts)).is_file()

    list_response = await client.get(
        "/api/v1/nodes", params={"parent_id": folder_id}, headers=auth_headers
    )
    assert [item["name"] for item in list_response.json()["items"]] == ["readme.txt"]

    await client.post(
        "/api/v1/nodes/upload",
        data={"parent_id": folder_id},
        files={"file": ("backup.zip", b"zip", "application/zip")},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/nodes/upload",
        data={"parent_id": folder_id},
        files={"file": ("installer.exe", b"exe", "application/octet-stream")},
        headers=auth_headers,
    )
    archive_list = await client.get(
        "/api/v1/nodes",
        params={"parent_id": folder_id, "file_type": "archive"},
        headers=auth_headers,
    )
    assert [item["name"] for item in archive_list.json()["items"]] == ["backup.zip"]
    executable_list = await client.get(
        "/api/v1/nodes",
        params={"parent_id": folder_id, "file_type": "executable"},
        headers=auth_headers,
    )
    assert [item["name"] for item in executable_list.json()["items"]] == ["installer.exe"]

    preview_response = await client.get(
        f"/api/v1/nodes/{file_id}/preview", headers=auth_headers
    )
    assert preview_response.status_code == 200
    assert preview_response.content == b"hello pan"

    share_response = await client.post(
        "/api/v1/shares",
        json={"node_id": file_id, "expires_in_days": 7},
        headers=auth_headers,
    )
    assert share_response.status_code == 201
    token = share_response.json()["token"]
    public_response = await client.get(f"/api/v1/public/shares/{token}")
    assert public_response.status_code == 200
    assert public_response.json()["root"]["name"] == "readme.txt"

    permanent_share = await client.post(
        "/api/v1/shares",
        json={"node_id": file_id, "expires_in_days": None},
        headers=auth_headers,
    )
    assert permanent_share.status_code == 201
    assert permanent_share.json()["expires_at"] is None
    assert permanent_share.json()["is_active"] is True
    permanent_token = permanent_share.json()["token"]
    permanent_public = await client.get(f"/api/v1/public/shares/{permanent_token}")
    assert permanent_public.status_code == 200
    assert permanent_public.json()["expires_at"] is None

    delete_response = await client.delete(f"/api/v1/nodes/{file_id}", headers=auth_headers)
    assert delete_response.status_code == 204
    assert (await client.get(f"/api/v1/public/shares/{token}")).status_code == 410

    trash_response = await client.get("/api/v1/trash", headers=auth_headers)
    assert [item["id"] for item in trash_response.json()] == [file_id]
    restore_response = await client.post(
        f"/api/v1/trash/{file_id}/restore", headers=auth_headers
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["parent_id"] == folder_id

    removable_share = await client.post(
        "/api/v1/shares",
        json={"node_id": file_id, "expires_in_days": 7},
        headers=auth_headers,
    )
    removable_share_id = removable_share.json()["id"]
    removable_token = removable_share.json()["token"]
    active_delete = await client.delete(
        f"/api/v1/shares/{removable_share_id}/record", headers=auth_headers
    )
    assert active_delete.status_code == 409
    assert (
        await client.delete(f"/api/v1/shares/{removable_share_id}", headers=auth_headers)
    ).status_code == 204
    assert (await client.get(f"/api/v1/public/shares/{removable_token}")).status_code == 410
    assert (
        await client.delete(
            f"/api/v1/shares/{removable_share_id}/record", headers=auth_headers
        )
    ).status_code == 204
    assert (await client.get(f"/api/v1/public/shares/{removable_token}")).status_code == 404
    assert (await client.get(f"/api/v1/nodes/{file_id}/preview", headers=auth_headers)).status_code == 200


async def test_private_nodes_do_not_leak_between_users(
    client: AsyncClient, auth_headers: dict[str, str]
):
    folder = await client.post(
        "/api/v1/nodes/folders",
        json={"name": "私密"},
        headers=auth_headers,
    )
    folder_id = folder.json()["id"]

    other = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "name": "Other", "password": "password123"},
    )
    other_headers = auth_header(other)
    response = await client.patch(
        f"/api/v1/nodes/{folder_id}/name", json={"name": "越权"}, headers=other_headers
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NODE_NOT_FOUND"


async def test_change_password_invalidates_old_token(
    client: AsyncClient, auth_headers: dict[str, str]
):
    wrong = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "new-password123"},
        headers=auth_headers,
    )
    assert wrong.status_code == 422
    assert wrong.json()["code"] == "CURRENT_PASSWORD_INVALID"

    changed = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "password123", "new_password": "new-password123"},
        headers=auth_headers,
    )
    assert changed.status_code == 200
    new_headers = auth_header(changed, token_version=1)

    assert (await client.get("/api/v1/auth/me", headers=auth_headers)).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers=new_headers)).status_code == 200
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "password123"},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "new-password123"},
    )
    assert new_login.status_code == 200


async def test_single_admin_requires_password_change(client: AsyncClient, session_factory):
    async with session_factory() as db:
        db.add(
            User(
                email="administrator@pan.internal",
                username="administrator",
                name="系统管理员",
                password_hash=hash_password("123456"),
                quota_bytes=0,
                is_admin=True,
                must_change_password=True,
                is_active=True,
            )
        )
        await db.commit()

    login = await client.post(
        "/api/v1/admin/login", json={"username": "administrator", "password": "123456"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["is_admin"] is True
    assert login.json()["user"]["must_change_password"] is True
    regular_login_rejects_admin = await client.post(
        "/api/v1/auth/login",
        json={"email": "administrator@pan.internal", "password": "123456"},
    )
    assert regular_login_rejects_admin.status_code == 401
    old_headers = auth_header(login)

    blocked = await client.get("/api/v1/admin/overview", headers=old_headers)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "PASSWORD_CHANGE_REQUIRED"

    changed = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "123456", "new_password": "new-admin-password"},
        headers=old_headers,
    )
    assert changed.status_code == 200
    assert changed.json()["user"]["must_change_password"] is False
    new_headers = auth_header(changed, token_version=1)
    overview = await client.get("/api/v1/admin/overview", headers=new_headers)
    assert overview.status_code == 200
    assert overview.json()["disk_total_bytes"] > 0
    assert 0 <= overview.json()["disk_free_bytes"] <= overview.json()["disk_total_bytes"]

    regular = await client.post(
        "/api/v1/auth/register",
        json={"email": "regular@example.com", "name": "Regular", "password": "password123"},
    )
    regular_headers = auth_header(regular)
    denied = await client.get("/api/v1/admin/overview", headers=regular_headers)
    assert denied.status_code == 403
    assert denied.json()["code"] == "ADMIN_REQUIRED"

    public_config = await client.get("/api/v1/system/config")
    assert public_config.status_code == 200
    assert public_config.json()["registration_enabled"] is True

    settings_response = await client.patch(
        "/api/v1/admin/settings",
        json={"registration_enabled": False},
        headers=new_headers,
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["registration_enabled"] is False
    assert (await client.get("/api/v1/system/config")).json()["registration_enabled"] is False

    blocked_registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "blocked@example.com", "name": "Blocked", "password": "password123"},
    )
    assert blocked_registration.status_code == 403
    assert blocked_registration.json()["code"] == "REGISTRATION_DISABLED"

    created = await client.post(
        "/api/v1/admin/users",
        json={"email": "assigned@example.com", "name": "Assigned"},
        headers=new_headers,
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["user"]["quota_bytes"] == 5 * 1024 * 1024 * 1024
    temporary_password = created_body["temporary_password"]
    assert len(temporary_password) >= 12

    assigned_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "assigned@example.com", "password": temporary_password},
    )
    assert assigned_login.status_code == 200
    assert assigned_login.json()["user"]["must_change_password"] is True
    temporary_headers = auth_header(assigned_login)
    password_required = await client.get("/api/v1/nodes", headers=temporary_headers)
    assert password_required.status_code == 403
    assert password_required.json()["code"] == "PASSWORD_CHANGE_REQUIRED"

    assigned_changed = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": temporary_password,
            "new_password": "assigned-new-password",
        },
        headers=temporary_headers,
    )
    assert assigned_changed.status_code == 200
    assigned_headers = auth_header(assigned_changed, token_version=1)
    assert (await client.get("/api/v1/nodes", headers=assigned_headers)).status_code == 200

    reset = await client.post(
        f"/api/v1/admin/users/{created_body['user']['id']}/reset-password",
        json={"password": "123456"},
        headers=new_headers,
    )
    assert reset.status_code == 200
    reset_password = reset.json()["temporary_password"]
    assert reset_password == "123456"
    assert (await client.get("/api/v1/auth/me", headers=assigned_headers)).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "assigned@example.com", "password": "assigned-new-password"},
        )
    ).status_code == 401
    reset_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "assigned@example.com", "password": reset_password},
    )
    assert reset_login.status_code == 200
    assert reset_login.json()["user"]["must_change_password"] is True


async def test_external_api_application_account_scope_findlist_and_usage(
    client: AsyncClient, auth_headers: dict[str, str], session_factory
):
    async with session_factory() as db:
        db.add(
            User(
                email="administrator@pan.internal",
                username="administrator",
                name="系统管理员",
                password_hash=hash_password("admin-password"),
                quota_bytes=0,
                is_admin=True,
                must_change_password=False,
                is_active=True,
            )
        )
        await db.commit()

    admin_login = await client.post(
        "/api/v1/admin/login",
        json={"username": "administrator", "password": "admin-password"},
    )
    admin_headers = auth_header(admin_login)
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    owner_id = me.json()["id"]

    contracts = await client.post(
        "/api/v1/nodes/folders", json={"name": "合同资料"}, headers=auth_headers
    )
    outside = await client.post(
        "/api/v1/nodes/folders", json={"name": "私有目录"}, headers=auth_headers
    )
    outside_file = await client.post(
        "/api/v1/nodes/upload",
        data={"parent_id": outside.json()["id"]},
        files={"file": ("private.txt", b"private", "text/plain")},
        headers=auth_headers,
    )

    other = await client.post(
        "/api/v1/auth/register",
        json={"email": "separate@example.com", "name": "Separate", "password": "password123"},
    )
    other_headers = auth_header(other)
    other_root = (await client.get("/api/v1/nodes", headers=other_headers)).json()[
        "current_folder"
    ]

    created = await client.post(
        "/api/v1/admin/integrations",
        json={
            "name": "测试业务系统",
            "user_id": owner_id,
            "can_read": True,
            "can_download": True,
            "can_upload": True,
            "can_manage": True,
            "can_delete": True,
        },
        headers=admin_headers,
    )
    assert created.status_code == 201
    application_id = created.json()["application"]["id"]
    api_key = created.json()["api_key"]
    api_headers = {"Authorization": f"Bearer {api_key}"}
    assert api_key.startswith("pan_")

    all_resources = await client.get("/api/v1/open/findlist", headers=api_headers)
    assert all_resources.status_code == 200
    assert {item["name"] for item in all_resources.json()["items"]} >= {
        "我的文件",
        "合同资料",
        "私有目录",
        "private.txt",
    }
    by_id = await client.get(
        "/api/v1/open/findlist",
        params={"node_id": outside_file.json()["id"]},
        headers=api_headers,
    )
    assert [item["name"] for item in by_id.json()["items"]] == ["private.txt"]
    by_parent = await client.get(
        "/api/v1/open/findlist",
        params={"parent_id": outside.json()["id"]},
        headers=api_headers,
    )
    assert [item["name"] for item in by_parent.json()["items"]] == ["private.txt"]
    by_keyword = await client.get(
        "/api/v1/open/findlist", params={"keyword": "private"}, headers=api_headers
    )
    assert [item["name"] for item in by_keyword.json()["items"]] == ["private.txt"]

    account_list = await client.get("/api/v1/open/nodes", headers=api_headers)
    assert account_list.status_code == 200
    assert {item["id"] for item in account_list.json()["items"]} >= {
        contracts.json()["id"],
        outside.json()["id"],
    }
    cross_account = await client.get(
        f"/api/v1/open/nodes/{other_root['id']}", headers=api_headers
    )
    assert cross_account.status_code == 404

    uploaded = await client.post(
        "/api/v1/open/upload",
        files={"file": ("external.txt", b"external data", "text/plain")},
        headers=api_headers,
    )
    assert uploaded.status_code == 201
    downloaded = await client.get(
        f"/api/v1/open/nodes/{uploaded.json()['id']}/download", headers=api_headers
    )
    assert downloaded.status_code == 200
    assert downloaded.content == b"external data"
    assert (
        await client.delete(
            f"/api/v1/open/nodes/{uploaded.json()['id']}", headers=api_headers
        )
    ).status_code == 204
    immutable_root = await client.delete(
        f"/api/v1/open/nodes/{account_list.json()['current_folder']['id']}",
        headers=api_headers,
    )
    assert immutable_root.status_code == 422
    assert immutable_root.json()["code"] == "ROOT_IMMUTABLE"

    applications = await client.get("/api/v1/admin/integrations", headers=admin_headers)
    usage = applications.json()["items"][0]
    assert usage["request_count"] >= 6
    assert usage["failed_request_count"] >= 2
    assert usage["upload_bytes"] == len(b"external data")
    assert usage["download_bytes"] == len(b"external data")
    assert usage["last_used_at"] is not None

    rotated = await client.post(
        f"/api/v1/admin/integrations/{application_id}/rotate-key", headers=admin_headers
    )
    assert rotated.status_code == 200
    new_headers = {"Authorization": f"Bearer {rotated.json()['api_key']}"}
    assert (await client.get("/api/v1/open/nodes", headers=api_headers)).status_code == 401
    assert (await client.get("/api/v1/open/nodes", headers=new_headers)).status_code == 200

    disabled = await client.patch(
        f"/api/v1/admin/integrations/{application_id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert disabled.status_code == 200
    assert (await client.get("/api/v1/open/nodes", headers=new_headers)).status_code == 403

    read_only = await client.post(
        "/api/v1/admin/integrations",
        json={
            "name": "只读系统",
            "user_id": owner_id,
            "can_read": True,
            "can_download": False,
            "can_upload": False,
            "can_manage": False,
            "can_delete": False,
        },
        headers=admin_headers,
    )
    read_headers = {"Authorization": f"Bearer {read_only.json()['api_key']}"}
    denied_write = await client.post(
        "/api/v1/open/folders", json={"name": "禁止创建"}, headers=read_headers
    )
    assert denied_write.status_code == 403
    assert denied_write.json()["code"] == "API_PERMISSION_DENIED"
    denied_download = await client.get(
        f"/api/v1/open/nodes/{outside_file.json()['id']}/download", headers=read_headers
    )
    assert denied_download.status_code == 403
    assert denied_download.json()["code"] == "API_PERMISSION_DENIED"

    download_only = await client.post(
        "/api/v1/admin/integrations",
        json={
            "name": "只下载系统",
            "user_id": owner_id,
            "can_read": False,
            "can_download": True,
            "can_upload": False,
            "can_manage": False,
            "can_delete": False,
        },
        headers=admin_headers,
    )
    download_headers = {"Authorization": f"Bearer {download_only.json()['api_key']}"}
    download_only_id = download_only.json()["application"]["id"]
    denied_read = await client.get("/api/v1/open/findlist", headers=download_headers)
    assert denied_read.status_code == 403
    assert denied_read.json()["code"] == "API_PERMISSION_DENIED"
    allowed_download = await client.get(
        f"/api/v1/open/nodes/{outside_file.json()['id']}/download",
        headers=download_headers,
    )
    assert allowed_download.status_code == 200

    deleted = await client.delete(
        f"/api/v1/admin/integrations/{download_only_id}", headers=admin_headers
    )
    assert deleted.status_code == 204
    assert (
        await client.get(
            f"/api/v1/open/nodes/{outside_file.json()['id']}/download",
            headers=download_headers,
        )
    ).status_code == 401
    missing = await client.delete(
        f"/api/v1/admin/integrations/{download_only_id}", headers=admin_headers
    )
    assert missing.status_code == 404


async def test_legacy_flat_file_migration(
    client: AsyncClient, auth_headers: dict[str, str], session_factory
):
    uploaded = await client.post(
        "/api/v1/nodes/upload",
        files={"file": ("legacy.txt", b"legacy data", "text/plain")},
        headers=auth_headers,
    )
    assert uploaded.status_code == 201
    node_id = uuid.UUID(uploaded.json()["id"])

    async with session_factory() as db:
        node = await db.get(Node, node_id)
        assert node is not None and node.storage_key is not None
        sharded_path = Path(settings.storage_path).joinpath(*node.storage_key.split("/"))
        object_id = node.storage_key.rsplit("/", 1)[-1]
        legacy_path = Path(settings.storage_path) / object_id
        sharded_path.replace(legacy_path)
        node.storage_key = object_id
        await db.commit()

    assert await migrate_legacy_storage_layout(session_factory) == 1
    async with session_factory() as db:
        node = await db.get(Node, node_id)
        assert node is not None and node.storage_key is not None
        assert node.storage_key.count("/") == 4
        assert not legacy_path.exists()
        assert Path(settings.storage_path).joinpath(*node.storage_key.split("/")).read_bytes() == b"legacy data"


async def test_empty_trash_removes_nested_files(
    client: AsyncClient, auth_headers: dict[str, str], session_factory
):
    folder = await client.post(
        "/api/v1/nodes/folders", json={"name": "待清空"}, headers=auth_headers
    )
    uploaded = await client.post(
        "/api/v1/nodes/upload",
        data={"parent_id": folder.json()["id"]},
        files={"file": ("purge.txt", b"purge me", "text/plain")},
        headers=auth_headers,
    )
    file_id = uuid.UUID(uploaded.json()["id"])
    async with session_factory() as db:
        node = await db.get(Node, file_id)
        assert node is not None and node.storage_key is not None
        stored_path = Path(settings.storage_path).joinpath(*node.storage_key.split("/"))
    assert stored_path.exists()

    assert (
        await client.delete(f"/api/v1/nodes/{folder.json()['id']}", headers=auth_headers)
    ).status_code == 204
    assert len((await client.get("/api/v1/trash", headers=auth_headers)).json()) == 1
    assert (await client.delete("/api/v1/trash", headers=auth_headers)).status_code == 204
    assert (await client.get("/api/v1/trash", headers=auth_headers)).json() == []
    assert not stored_path.exists()


async def test_default_sort_shows_latest_updated_first(
    client: AsyncClient, auth_headers: dict[str, str]
):
    first = await client.post(
        "/api/v1/nodes/upload",
        files={"file": ("first.txt", b"first", "text/plain")},
        headers=auth_headers,
    )
    second = await client.post(
        "/api/v1/nodes/upload",
        files={"file": ("second.txt", b"second", "text/plain")},
        headers=auth_headers,
    )
    assert first.status_code == 201 and second.status_code == 201

    initial = await client.get("/api/v1/nodes", headers=auth_headers)
    assert [item["name"] for item in initial.json()["items"]] == ["second.txt", "first.txt"]

    renamed = await client.patch(
        f"/api/v1/nodes/{first.json()['id']}/name",
        json={"name": "first-updated.txt"},
        headers=auth_headers,
    )
    assert renamed.status_code == 200
    updated = await client.get("/api/v1/nodes", headers=auth_headers)
    assert [item["name"] for item in updated.json()["items"]] == [
        "first-updated.txt",
        "second.txt",
    ]

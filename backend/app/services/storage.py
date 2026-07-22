import os
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError


def storage_root() -> Path:
    root = Path(settings.storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def storage_key(identifier: str | None = None, created_at: datetime | None = None) -> str:
    """Build a balanced, date-partitioned relative key for a stored object."""
    object_id = identifier or uuid.uuid4().hex
    timestamp = created_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    timestamp = timestamp.astimezone(UTC)
    return f"{timestamp:%Y/%m/%d}/{object_id[:2]}/{object_id}"


def storage_path(key: str) -> Path:
    """Resolve a database storage key while preventing paths outside the storage root."""
    if not key or "\\" in key:
        raise AppError(500, "INVALID_STORAGE_KEY", "文件存储路径无效")
    relative = PurePosixPath(key)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        raise AppError(500, "INVALID_STORAGE_KEY", "文件存储路径无效")
    root = storage_root()
    target = (root / Path(*relative.parts)).resolve(strict=False)
    if target == root or root not in target.parents:
        raise AppError(500, "INVALID_STORAGE_KEY", "文件存储路径无效")
    return target


def _prepare_target(key: str) -> Path:
    target = storage_path(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _prune_empty_parents(path: Path) -> None:
    root = storage_root()
    parent = path.parent
    while parent != root and root in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


async def save_upload(upload: UploadFile) -> tuple[str, int]:
    key = storage_key()
    target = _prepare_target(key)
    size = 0
    try:
        async with aiofiles.open(target, "wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_file_size_bytes:
                    raise AppError(413, "FILE_TOO_LARGE", "文件超过单文件大小限制")
                await output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        _prune_empty_parents(target)
        raise
    finally:
        await upload.close()
    return key, size


def copy_stored_file(source_key: str) -> str:
    new_key = storage_key()
    shutil.copy2(storage_path(source_key), _prepare_target(new_key))
    return new_key


def delete_stored_file(key: str | None) -> None:
    if key:
        target = storage_path(key)
        target.unlink(missing_ok=True)
        _prune_empty_parents(target)


def stored_file_exists(key: str | None) -> bool:
    return bool(key and os.path.isfile(storage_path(key)))

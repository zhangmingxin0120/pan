import os
import shutil
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError


def storage_root() -> Path:
    root = Path(settings.storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def storage_path(key: str) -> Path:
    return storage_root() / key


async def save_upload(upload: UploadFile) -> tuple[str, int]:
    key = uuid.uuid4().hex
    target = storage_path(key)
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
        raise
    finally:
        await upload.close()
    return key, size


def copy_stored_file(source_key: str) -> str:
    new_key = uuid.uuid4().hex
    shutil.copy2(storage_path(source_key), storage_path(new_key))
    return new_key


def delete_stored_file(key: str | None) -> None:
    if key:
        storage_path(key).unlink(missing_ok=True)


def stored_file_exists(key: str | None) -> bool:
    return bool(key and os.path.isfile(storage_path(key)))


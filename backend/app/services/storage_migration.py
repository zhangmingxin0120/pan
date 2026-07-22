import os
from datetime import UTC

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Node, NodeKind
from app.services.storage import storage_key, storage_path


async def migrate_legacy_storage_layout(session_factory=SessionLocal) -> int:
    """Move legacy flat objects into date/hash partitions; safe to resume after interruption."""
    migrated = 0
    async with session_factory() as db:
        nodes = list(
            (
                await db.scalars(
                    select(Node).where(Node.kind == NodeKind.FILE, Node.storage_key.is_not(None))
                )
            ).all()
        )
        for node in nodes:
            old_key = node.storage_key
            if not old_key or "/" in old_key:
                continue
            created_at = node.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            new_key = storage_key(old_key, created_at)
            source = storage_path(old_key)
            target = storage_path(new_key)

            if source.exists() and target.exists():
                raise RuntimeError(f"Storage migration collision for object {old_key}")
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, target)
            elif not target.exists():
                # Keep the legacy key so missing-file diagnostics continue to reference its old location.
                continue

            node.storage_key = new_key
            migrated += 1
        await db.commit()
    return migrated

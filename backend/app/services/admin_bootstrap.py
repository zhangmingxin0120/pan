from sqlalchemy import func, select, update

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User


async def ensure_single_admin() -> None:
    """Create the built-in administrator without resetting a changed password."""
    username = settings.admin_username.strip().lower()
    async with SessionLocal() as db:
        admin = await db.scalar(select(User).where(func.lower(User.username) == username))
        if admin is None:
            admin = await db.scalar(select(User).where(User.is_admin.is_(True)))
            if admin is not None:
                admin.username = username
            else:
                admin = User(
                    email=settings.admin_email.lower(),
                    username=username,
                    name="系统管理员",
                    password_hash=hash_password(settings.admin_initial_password),
                    quota_bytes=0,
                    is_admin=True,
                    must_change_password=True,
                    is_active=True,
                )
                db.add(admin)
                await db.flush()
        await db.execute(
            update(User).where(User.id != admin.id, User.is_admin.is_(True)).values(is_admin=False)
        )
        admin.is_admin = True
        admin.is_active = True
        await db.commit()

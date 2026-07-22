from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemSetting


async def get_system_settings(db: AsyncSession) -> SystemSetting:
    settings = await db.get(SystemSetting, 1)
    if settings is None:
        settings = SystemSetting(id=1, registration_enabled=True)
        db.add(settings)
        await db.flush()
    return settings

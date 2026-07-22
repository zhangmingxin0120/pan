from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.system import PublicSystemConfigResponse
from app.services.system_settings import get_system_settings

router = APIRouter(prefix="/system", tags=["系统"])


@router.get("/config", response_model=PublicSystemConfigResponse)
async def public_config(db: AsyncSession = Depends(get_db)):
    settings = await get_system_settings(db)
    return PublicSystemConfigResponse(registration_enabled=settings.registration_enabled)

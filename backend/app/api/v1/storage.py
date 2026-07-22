from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.node import StorageUsageResponse
from app.services.nodes import used_bytes

router = APIRouter(prefix="/storage", tags=["空间"])


@router.get("/usage", response_model=StorageUsageResponse)
async def usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return StorageUsageResponse(used_bytes=await used_bytes(db, user.id), quota_bytes=user.quota_bytes)


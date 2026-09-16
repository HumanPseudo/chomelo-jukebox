from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.profile import ListenHistoryItem, ProfileOut, ProfileUpdate
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.user import User
from app.services import profile_service

router = APIRouter(prefix="/users", tags=["users", "profile"])


@router.get("/me/profile", response_model=ProfileOut)
async def my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    return await profile_service.get_profile(db, current_user)


@router.patch("/me/profile", response_model=ProfileOut)
async def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    return await profile_service.update_profile(db, current_user, payload)


@router.get("/me/listen-history", response_model=list[ListenHistoryItem])
async def my_listen_history(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ListenHistoryItem]:
    return await profile_service.listen_history(db, current_user, limit=limit)

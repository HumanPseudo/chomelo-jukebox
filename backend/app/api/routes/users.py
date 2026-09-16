from fastapi import APIRouter, Depends

from app.api.schemas.auth import UserOut
from app.core.security import get_current_user
from app.domain.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        display_name=current_user.profile.display_name if current_user.profile else "",
    )

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.db.session import get_db
from app.services import audit_service
from app.services.auth_service import authenticate, issue_tokens, refresh_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await register_user(db, payload)
    await audit_service.log_action(
        db, action="auth.register", user_id=user.id, detail={"email": user.email}, request=request
    )
    await db.commit()
    return issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await authenticate(
        db, payload, client_ip=request.client.host if request.client else None
    )
    await audit_service.log_action(db, action="auth.login", user_id=user.id, request=request)
    await db.commit()
    return issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await refresh_user(db, payload.refresh_token)
    await audit_service.log_action(db, action="auth.refresh", user_id=user.id, request=request)
    await db.commit()
    return issue_tokens(user)

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.db.session import get_db
from app.services.auth_service import authenticate, issue_tokens, refresh_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await register_user(db, payload)
    return issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    client_ip = request.client.host if request.client else None
    user = await authenticate(db, payload, client_ip=client_ip)
    return issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await refresh_user(db, payload.refresh_token)
    return issue_tokens(user)

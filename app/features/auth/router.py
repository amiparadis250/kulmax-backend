from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, require_roles
from app.core.db import get_session
from app.core.errors import ERROR_RESPONSES
from app.core.roles import ALL_ROLES
from app.features.auth import service
from app.features.auth.schemas import LoginRequest, MeRead, RefreshRequest, TokenResponse
from app.features.users import service as users_service

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)


# Public: no require_roles (you cannot have a role before logging in).
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    return await service.login(session, data.email, data.password)


# Public: authenticated by the refresh token in the body.
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    return await service.refresh(session, data.refresh_token)


@router.get("/me", response_model=MeRead)
async def me(
    user: CurrentUser = Depends(require_roles(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> MeRead:
    return MeRead.model_validate(await users_service.get_user(session, user.id))

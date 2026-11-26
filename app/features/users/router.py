import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, require_roles
from app.core.db import get_session
from app.core.errors import ERROR_RESPONSES
from app.core.pagination import Page, PageParams, page_params
from app.core.roles import ADMINS, Role
from app.features.users import service
from app.features.users.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], responses=ERROR_RESPONSES)


@router.get("", response_model=Page[UserRead], dependencies=[Depends(require_roles(*ADMINS))])
async def list_users(
    params: PageParams = Depends(page_params),
    role: Role | None = None,
    is_active: bool | None = None,
    q: str | None = Query(None, max_length=100, description="Search name or email"),
    session: AsyncSession = Depends(get_session),
) -> Page[UserRead]:
    users, total = await service.list_users(
        session, params, role=role, is_active=is_active, search=q
    )
    return Page(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        page=params.page,
        limit=params.limit,
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*ADMINS))],
)
async def create_user(data: UserCreate, session: AsyncSession = Depends(get_session)) -> UserRead:
    return UserRead.model_validate(await service.create_user(session, data))


@router.get("/{user_id}", response_model=UserRead, dependencies=[Depends(require_roles(*ADMINS))])
async def get_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> UserRead:
    return UserRead.model_validate(await service.get_user(session, user_id))


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    actor: CurrentUser = Depends(require_roles(*ADMINS)),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    return UserRead.model_validate(await service.update_user(session, user_id, data, actor=actor))

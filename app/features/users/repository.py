"""DB queries for users. Only `users.service` may import this module."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Role
from app.features.users.models import User


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    *,
    offset: int,
    limit: int,
    role: Role | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> tuple[Sequence[User], int]:
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))

    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    result = await session.execute(
        query.order_by(User.full_name, User.id).offset(offset).limit(limit)
    )
    return result.scalars().all(), total or 0


async def count_active_admins(session: AsyncSession) -> int:
    count = await session.scalar(
        select(func.count()).where(User.role == Role.ADMIN, User.is_active.is_(True))
    )
    return count or 0


def add(session: AsyncSession, user: User) -> None:
    session.add(user)

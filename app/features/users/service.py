"""Business rules for users. This module is the public interface of the `users` feature:
other features (and `core.auth`) call these functions, never the repository.

Services own the transaction: write operations commit before returning.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams
from app.core.roles import Role
from app.core.security import hash_password, verify_password
from app.core.time import utcnow
from app.features.users import repository
from app.features.users.models import User
from app.features.users.schemas import UserCreate, UserUpdate


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await repository.get_by_id(session, user_id)
    if user is None:
        raise NotFoundError("User not found", details={"user_id": str(user_id)})
    return user


async def get_active_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    user = await repository.get_by_id(session, user_id)
    return user if user is not None and user.is_active else None


async def list_users(
    session: AsyncSession,
    params: PageParams,
    *,
    role: Role | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> tuple[Sequence[User], int]:
    return await repository.list_users(
        session,
        offset=params.offset,
        limit=params.limit,
        role=role,
        is_active=is_active,
        search=search,
    )


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    email = _normalize_email(data.email)
    if await repository.get_by_email(session, email) is not None:
        raise ConflictError("A user with this email already exists", code="email_taken")
    user = User(
        email=email,
        full_name=data.full_name.strip(),
        phone=data.phone,
        role=data.role,
        password_hash=hash_password(data.password),
        is_active=True,
    )
    repository.add(session, user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession, user_id: uuid.UUID, data: UserUpdate, *, actor: CurrentUser
) -> User:
    user = await get_user(session, user_id)
    changes = data.model_dump(exclude_unset=True)

    is_self = user.id == actor.id
    if is_self and changes.get("is_active") is False:
        raise BusinessRuleError("You cannot deactivate your own account", code="cannot_modify_self")
    if is_self and "role" in changes and changes["role"] != user.role:
        raise BusinessRuleError("You cannot change your own role", code="cannot_modify_self")

    loses_admin = (
        user.role == Role.ADMIN
        and user.is_active
        and (
            ("role" in changes and changes["role"] != Role.ADMIN)
            or changes.get("is_active") is False
        )
    )
    if loses_admin and await repository.count_active_admins(session) <= 1:
        raise BusinessRuleError("There must always be at least one active admin", code="last_admin")

    if "password" in changes:
        user.password_hash = hash_password(changes.pop("password"))
    if "full_name" in changes:
        changes["full_name"] = changes["full_name"].strip()
    for field, value in changes.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    """Return the user if the credentials are valid and the account is active, else None.
    Records `last_login_at` on success."""
    user = await repository.get_by_email(session, _normalize_email(email))
    if not verify_password(password, user.password_hash if user else None):
        return None
    if user is None or not user.is_active:
        return None
    user.last_login_at = utcnow()
    await session.commit()
    await session.refresh(user)
    return user


async def seed_admin(
    session: AsyncSession, *, email: str, full_name: str, password: str
) -> tuple[User, bool]:
    """Create the first admin. Idempotent: if the email exists, returns (user, False) unchanged."""
    existing = await repository.get_by_email(session, _normalize_email(email))
    if existing is not None:
        return existing, False
    user = await create_user(
        session,
        UserCreate(email=email, full_name=full_name, role=Role.ADMIN, password=password),
    )
    return user, True

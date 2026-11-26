"""Auth dependencies: `get_current_user` and `require_roles(...)`.

Every route declares its allowed roles:

    @router.get("", dependencies=[Depends(require_roles(*ALL_ROLES))])
    # or, when the handler needs the user:
    user: CurrentUser = Depends(require_roles(Role.ADMIN))
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.roles import Role
from app.core.security import decode_token

_bearer = HTTPBearer(auto_error=False, description="Access token from POST /api/v1/auth/login")


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated user, as seen by every feature. Not an ORM object."""

    id: uuid.UUID
    email: str
    full_name: str
    role: Role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    # Imported here: users depends on core, and core reaches users only through its service.
    from app.features.users import service as users_service

    if credentials is None:
        raise AuthenticationError("Not authenticated")
    payload = decode_token(credentials.credentials, expected_type="access")
    user = await users_service.get_active_user(session, payload.user_id)
    if user is None:
        raise AuthenticationError("User not found or inactive", code="invalid_token")
    return CurrentUser(id=user.id, email=user.email, full_name=user.full_name, role=user.role)


def require_roles(*roles: Role) -> Callable[..., Awaitable[CurrentUser]]:
    allowed = frozenset(roles)

    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise PermissionDeniedError("You do not have permission to do this")
        return user

    return dependency

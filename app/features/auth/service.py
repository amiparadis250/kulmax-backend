"""Login and token refresh. Auth owns no tables: it reads users through `users.service`.

Tokens are stateless JWTs (see docs/decisions/0005-stateless-jwt-tokens.md). A deactivated
user is rejected on the next request because `is_active` is checked on every token use.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError
from app.core.security import create_token, decode_token
from app.features.auth.schemas import TokenResponse
from app.features.users import service as users_service


def _issue_tokens(user_id: uuid.UUID) -> TokenResponse:
    access, expires_in = create_token(user_id, "access")
    refresh, _ = create_token(user_id, "refresh")
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expires_in)


async def login(session: AsyncSession, email: str, password: str) -> TokenResponse:
    user = await users_service.authenticate(session, email, password)
    if user is None:
        # Same message for unknown email, wrong password and inactive account.
        raise AuthenticationError("Invalid email or password", code="invalid_credentials")
    return _issue_tokens(user.id)


async def refresh(session: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token, expected_type="refresh")
    user = await users_service.get_active_user(session, payload.user_id)
    if user is None:
        raise AuthenticationError("User not found or inactive", code="invalid_token")
    return _issue_tokens(user.id)

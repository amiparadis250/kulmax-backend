"""Password hashing (argon2) and JWT encoding/decoding. No database access here."""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.core.time import utcnow

TokenType = Literal["access", "refresh"]

_password_hash = PasswordHash((Argon2Hasher(),))

# Used to spend the same time verifying when the user does not exist (no user enumeration).
_DUMMY_HASH = _password_hash.hash("kulmax-dummy-password")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


@dataclass(frozen=True)
class TokenPayload:
    user_id: uuid.UUID
    token_type: TokenType


def create_token(user_id: uuid.UUID, token_type: TokenType) -> tuple[str, int]:
    """Return (token, lifetime_in_seconds)."""
    settings = get_settings()
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == "access"  # noqa: S105 - token kind, not a secret
        else timedelta(days=settings.refresh_token_days)
    )
    now = utcnow()
    claims = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(lifetime.total_seconds())


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "type", "exp"]},
        )
        user_id = uuid.UUID(claims["sub"])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired", code="token_expired") from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise AuthenticationError("Invalid token", code="invalid_token") from exc
    if claims["type"] != expected_type:
        raise AuthenticationError("Wrong token type", code="invalid_token")
    return TokenPayload(user_id=user_id, token_type=expected_type)

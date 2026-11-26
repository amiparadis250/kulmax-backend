from datetime import timedelta
from typing import Any

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.roles import Role
from app.core.security import create_token
from app.core.time import utcnow
from app.features.users.models import User
from tests.conftest import DEFAULT_PASSWORD, MakeUser, auth_headers


async def _login(
    client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD
) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"status": response.status_code, "body": response.json()}


# --- login -------------------------------------------------------------------------------


async def test_login_returns_tokens_and_records_last_login(
    client: AsyncClient, staff: User
) -> None:
    result = await _login(client, staff.email)

    assert result["status"] == 200
    body = result["body"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == get_settings().access_token_minutes * 60
    assert body["access_token"]
    assert body["refresh_token"]

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.json()["last_login_at"] is not None


async def test_login_email_is_case_insensitive(client: AsyncClient, staff: User) -> None:
    result = await _login(client, staff.email.upper())
    assert result["status"] == 200


@pytest.mark.parametrize("case", ["wrong_password", "unknown_email", "inactive_user"])
async def test_login_failures_all_look_the_same(
    client: AsyncClient, make_user: MakeUser, case: str
) -> None:
    active = await make_user(Role.STAFF)
    inactive = await make_user(Role.STAFF, is_active=False)
    email, password = {
        "wrong_password": (active.email, "wrong-password"),
        "unknown_email": ("nobody@kulmax.rw", DEFAULT_PASSWORD),
        "inactive_user": (inactive.email, DEFAULT_PASSWORD),
    }[case]

    result = await _login(client, email, password)

    assert result["status"] == 401
    assert result["body"]["error"] == {
        "code": "invalid_credentials",
        "message": "Invalid email or password",
        "details": {},
    }


# --- /me ---------------------------------------------------------------------------------


@pytest.mark.parametrize("role", list(Role))
async def test_me_returns_current_user_for_every_role(
    client: AsyncClient, make_user: MakeUser, role: Role
) -> None:
    user = await make_user(role, full_name="Me Myself", phone="0788111222")

    response = await client.get("/api/v1/auth/me", headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["role"] == role.value
    assert body["full_name"] == "Me Myself"
    assert body["phone"] == "0788111222"


async def test_me_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_rejects_refresh_token(client: AsyncClient, staff: User) -> None:
    refresh, _ = create_token(staff.id, "refresh")
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_me_rejects_expired_token(client: AsyncClient, staff: User) -> None:
    settings = get_settings()
    expired = jwt.encode(
        {"sub": str(staff.id), "type": "access", "exp": utcnow() - timedelta(seconds=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


@pytest.mark.parametrize(
    "token",
    [
        "garbage",
        jwt.encode(
            {"sub": "x", "type": "access", "exp": 9999999999},
            "a-different-secret-that-is-long-enough-0123456789",
        ),
    ],
)
async def test_me_rejects_invalid_tokens(client: AsyncClient, token: str) -> None:
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


# --- refresh -----------------------------------------------------------------------------


async def test_refresh_issues_new_tokens(client: AsyncClient, staff: User) -> None:
    login = (await _login(client, staff.email))["body"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] != login["access_token"]
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200


async def test_refresh_rejects_access_token(client: AsyncClient, staff: User) -> None:
    access, _ = create_token(staff.id, "access")
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401


async def test_refresh_rejects_deactivated_user(client: AsyncClient, make_user: MakeUser) -> None:
    user = await make_user(Role.STAFF, is_active=False)
    refresh, _ = create_token(user.id, "refresh")
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 401

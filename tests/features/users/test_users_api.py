import uuid

import pytest
from httpx import AsyncClient

from app.core.roles import Role
from app.features.users.models import User
from tests.conftest import MakeUser, auth_headers


def _new_user(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "email": "Jean.Driver@Kulmax.RW",
        "full_name": "  Jean Mugabo ",
        "phone": "+250 788 123 456",
        "role": "staff",
        "password": "a-strong-password",
    }
    body.update(overrides)
    return body


# --- permissions -------------------------------------------------------------------------


async def test_requests_without_token_get_401_with_error_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users")
    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "not_authenticated", "message": "Not authenticated", "details": {}}
    }


@pytest.mark.parametrize("role", [Role.MANAGER, Role.STAFF])
async def test_non_admins_cannot_manage_users(
    client: AsyncClient, make_user: MakeUser, admin: User, role: Role
) -> None:
    headers = auth_headers(await make_user(role))
    calls = [
        client.get("/api/v1/users", headers=headers),
        client.post("/api/v1/users", json=_new_user(), headers=headers),
        client.get(f"/api/v1/users/{admin.id}", headers=headers),
        client.patch(f"/api/v1/users/{admin.id}", json={"full_name": "X"}, headers=headers),
    ]
    for call in calls:
        response = await call
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_denied"


# --- create ------------------------------------------------------------------------------


async def test_admin_creates_user(client: AsyncClient, admin: User) -> None:
    response = await client.post("/api/v1/users", json=_new_user(), headers=auth_headers(admin))

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jean.driver@kulmax.rw"
    assert body["full_name"] == "Jean Mugabo"
    assert body["phone"] == "+250788123456"
    assert body["role"] == "staff"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body


async def test_duplicate_email_is_rejected_case_insensitively(
    client: AsyncClient, admin: User
) -> None:
    headers = auth_headers(admin)
    await client.post("/api/v1/users", json=_new_user(), headers=headers)

    response = await client.post(
        "/api/v1/users", json=_new_user(email="JEAN.driver@kulmax.rw"), headers=headers
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "not-an-email"),
        ("password", "short"),
        ("role", "driver"),
        ("phone", "12ab"),
        ("full_name", ""),
    ],
)
async def test_create_validates_input(
    client: AsyncClient, admin: User, field: str, value: str
) -> None:
    response = await client.post(
        "/api/v1/users", json=_new_user(**{field: value}), headers=auth_headers(admin)
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert any(field in e["loc"] for e in error["details"]["errors"])


# --- read / list -------------------------------------------------------------------------


async def test_get_unknown_user_returns_404(client: AsyncClient, admin: User) -> None:
    response = await client.get(f"/api/v1/users/{uuid.uuid4()}", headers=auth_headers(admin))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_list_paginates_and_filters(
    client: AsyncClient, admin: User, make_user: MakeUser
) -> None:
    await make_user(Role.STAFF, full_name="Alice Staff")
    await make_user(Role.STAFF, full_name="Bob Staff", is_active=False)
    await make_user(Role.MANAGER, full_name="Carol Manager")
    headers = auth_headers(admin)

    everyone = (await client.get("/api/v1/users?limit=2&page=1", headers=headers)).json()
    assert everyone["total"] == 4
    assert everyone["page"] == 1
    assert everyone["limit"] == 2
    assert len(everyone["items"]) == 2

    page_two = (await client.get("/api/v1/users?limit=2&page=2", headers=headers)).json()
    assert len(page_two["items"]) == 2
    assert {u["id"] for u in page_two["items"]}.isdisjoint({u["id"] for u in everyone["items"]})

    staff = (await client.get("/api/v1/users?role=staff", headers=headers)).json()
    assert {u["full_name"] for u in staff["items"]} == {"Alice Staff", "Bob Staff"}

    active_staff = (
        await client.get("/api/v1/users?role=staff&is_active=true", headers=headers)
    ).json()
    assert [u["full_name"] for u in active_staff["items"]] == ["Alice Staff"]

    search = (await client.get("/api/v1/users?q=carol", headers=headers)).json()
    assert [u["full_name"] for u in search["items"]] == ["Carol Manager"]


async def test_list_rejects_limit_over_100(client: AsyncClient, admin: User) -> None:
    response = await client.get("/api/v1/users?limit=101", headers=auth_headers(admin))
    assert response.status_code == 422


# --- update ------------------------------------------------------------------------------


async def test_admin_updates_user_fields(
    client: AsyncClient, admin: User, make_user: MakeUser
) -> None:
    user = await make_user(Role.STAFF, phone="0788000000")

    response = await client.patch(
        f"/api/v1/users/{user.id}",
        json={"full_name": "New Name", "role": "manager", "phone": None},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "New Name"
    assert body["role"] == "manager"
    assert body["phone"] is None


async def test_update_rejects_null_for_required_fields(
    client: AsyncClient, admin: User, staff: User
) -> None:
    response = await client.patch(
        f"/api/v1/users/{staff.id}", json={"full_name": None}, headers=auth_headers(admin)
    )
    assert response.status_code == 422


async def test_admin_can_reset_password(client: AsyncClient, admin: User, staff: User) -> None:
    await client.patch(
        f"/api/v1/users/{staff.id}",
        json={"password": "brand-new-password"},
        headers=auth_headers(admin),
    )

    response = await client.post(
        "/api/v1/auth/login", json={"email": staff.email, "password": "brand-new-password"}
    )
    assert response.status_code == 200


async def test_admin_cannot_deactivate_self(client: AsyncClient, admin: User) -> None:
    response = await client.patch(
        f"/api/v1/users/{admin.id}", json={"is_active": False}, headers=auth_headers(admin)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "cannot_modify_self"


async def test_admin_cannot_change_own_role(client: AsyncClient, admin: User) -> None:
    response = await client.patch(
        f"/api/v1/users/{admin.id}", json={"role": "staff"}, headers=auth_headers(admin)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "cannot_modify_self"


async def test_admin_can_demote_another_admin_when_one_remains(
    client: AsyncClient, admin: User, make_user: MakeUser
) -> None:
    other_admin = await make_user(Role.ADMIN)
    response = await client.patch(
        f"/api/v1/users/{other_admin.id}", json={"role": "manager"}, headers=auth_headers(admin)
    )
    assert response.status_code == 200


async def test_deactivated_user_token_is_rejected(
    client: AsyncClient, admin: User, staff: User
) -> None:
    staff_headers = auth_headers(staff)
    await client.patch(
        f"/api/v1/users/{staff.id}", json={"is_active": False}, headers=auth_headers(admin)
    )

    response = await client.get("/api/v1/auth/me", headers=staff_headers)
    assert response.status_code == 401

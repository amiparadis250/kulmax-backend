"""Rules that cannot be reached through the API alone are tested at the service level."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.errors import BusinessRuleError
from app.core.roles import Role
from app.features.users import service
from app.features.users.models import User
from app.features.users.schemas import UserUpdate
from tests.conftest import MakeUser


def _actor(user: User) -> CurrentUser:
    return CurrentUser(id=user.id, email=user.email, full_name=user.full_name, role=user.role)


async def test_last_active_admin_cannot_be_demoted(
    session: AsyncSession, admin: User, manager: User
) -> None:
    with pytest.raises(BusinessRuleError) as exc_info:
        await service.update_user(
            session, admin.id, UserUpdate(role=Role.STAFF), actor=_actor(manager)
        )
    assert exc_info.value.code == "last_admin"


async def test_last_active_admin_cannot_be_deactivated(
    session: AsyncSession, admin: User, manager: User
) -> None:
    with pytest.raises(BusinessRuleError) as exc_info:
        await service.update_user(
            session, admin.id, UserUpdate(is_active=False), actor=_actor(manager)
        )
    assert exc_info.value.code == "last_admin"


async def test_inactive_admins_do_not_count_as_remaining(
    session: AsyncSession, admin: User, manager: User, make_user: MakeUser
) -> None:
    await make_user(Role.ADMIN, is_active=False)
    with pytest.raises(BusinessRuleError):
        await service.update_user(
            session, admin.id, UserUpdate(is_active=False), actor=_actor(manager)
        )


async def test_seed_admin_creates_admin_once(session: AsyncSession) -> None:
    user, created = await service.seed_admin(
        session, email="Boss@Kulmax.rw", full_name="Boss", password="a-strong-password"
    )
    assert created is True
    assert user.role == Role.ADMIN
    assert user.email == "boss@kulmax.rw"
    assert user.is_active is True

    again, created_again = await service.seed_admin(
        session, email="boss@kulmax.rw", full_name="Someone Else", password="another-password"
    )
    assert created_again is False
    assert again.id == user.id
    assert again.full_name == "Boss"


async def test_seed_admin_does_not_change_an_existing_non_admin(
    session: AsyncSession, staff: User
) -> None:
    user, created = await service.seed_admin(
        session, email=staff.email, full_name="X", password="a-strong-password"
    )
    assert created is False
    assert user.role == Role.STAFF

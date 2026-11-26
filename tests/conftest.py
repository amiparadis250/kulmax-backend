"""Test setup.

- The test database (TEST_DATABASE_URL, name must end in `_test`) is dropped, recreated and
  migrated with Alembic once per test run, so migrations are tested on every run.
- Each test runs inside a transaction that is rolled back at the end. Service `commit()` calls
  only release a savepoint, so tests never see each other's data.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.core.db import get_session
from app.core.roles import Role
from app.core.security import create_token
from app.features.users import service as users_service
from app.features.users.models import User
from app.features.users.schemas import UserCreate
from app.main import create_app

TEST_DATABASE_URL = get_settings().test_database_url
DEFAULT_PASSWORD = "correct-horse-1"


async def _recreate_test_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    name = url.database
    if not name or not name.endswith("_test"):
        raise RuntimeError(f"Refusing to wipe database {name!r}: its name must end with '_test'")
    admin = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=pool.NullPool
    )
    async with admin.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    asyncio.run(_recreate_test_database())
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=pool.NullPool)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        db_session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield db_session
        finally:
            await db_session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def _override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


MakeUser = Callable[..., Awaitable[User]]


@pytest.fixture
def make_user(session: AsyncSession) -> MakeUser:
    async def _make(
        role: Role = Role.STAFF,
        *,
        email: str | None = None,
        full_name: str = "Test User",
        phone: str | None = None,
        password: str = DEFAULT_PASSWORD,
        is_active: bool = True,
    ) -> User:
        user = await users_service.create_user(
            session,
            UserCreate(
                email=email or f"{role}-{uuid.uuid4().hex[:8]}@kulmax.rw",
                full_name=full_name,
                phone=phone,
                role=role,
                password=password,
            ),
        )
        if not is_active:
            user.is_active = False
            await session.commit()
        return user

    return _make


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_token(user.id, "access")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin(make_user: MakeUser) -> User:
    return await make_user(Role.ADMIN, full_name="Ada Admin")


@pytest.fixture
async def manager(make_user: MakeUser) -> User:
    return await make_user(Role.MANAGER, full_name="Max Manager")


@pytest.fixture
async def staff(make_user: MakeUser) -> User:
    return await make_user(Role.STAFF, full_name="Sam Staff")

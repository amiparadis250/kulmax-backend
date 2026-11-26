"""Create the DATABASE_URL database if it does not exist: `python tasks.py createdb`.

Connects to the server's `postgres` maintenance database, so the user needs CREATEDB.
"""

import asyncio

from sqlalchemy import pool, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


async def create_database() -> None:
    url = make_url(get_settings().database_url)
    name = url.database
    engine = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=pool.NullPool
    )
    async with engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        )
        if exists:
            print(f"Database {name!r} already exists")
        else:
            await conn.execute(text(f'CREATE DATABASE "{name}"'))
            print(f"Created database {name!r}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_database())

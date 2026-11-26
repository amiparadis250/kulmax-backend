"""Command line for the users feature.

    uv run python tasks.py seed-admin --email admin@kulmax.rw --full-name "Admin"

The password comes from --password, else SEED_ADMIN_PASSWORD (env or .env), else a prompt.
"""

import argparse
import asyncio
import getpass
import sys

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.db import get_engine, get_session_factory
from app.features.users import service


async def _seed_admin(email: str, full_name: str, password: str) -> int:
    try:
        async with get_session_factory()() as session:
            user, created = await service.seed_admin(
                session, email=email, full_name=full_name, password=password
            )
    except ValidationError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 1
    finally:
        await get_engine().dispose()
    if created:
        print(f"Created admin {user.email} ({user.id})")
    else:
        print(f"User {user.email} already exists (role: {user.role}); nothing changed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="users")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed-admin", help="Create the first admin user (idempotent)")
    seed.add_argument("--email", required=True)
    seed.add_argument("--full-name", required=True)
    seed.add_argument("--password", help="Prefer SEED_ADMIN_PASSWORD or the prompt")
    args = parser.parse_args(argv)

    password = args.password or get_settings().seed_admin_password
    if not password:
        password = getpass.getpass("Admin password (min 8 chars): ")
    return asyncio.run(_seed_admin(args.email, args.full_name, password))


if __name__ == "__main__":
    sys.exit(main())

"""User roles. Shared by every router's `require_roles(...)`; owned conceptually by `users`."""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"


ALL_ROLES: tuple[Role, ...] = (Role.ADMIN, Role.MANAGER, Role.STAFF)
MANAGERS: tuple[Role, ...] = (Role.ADMIN, Role.MANAGER)
ADMINS: tuple[Role, ...] = (Role.ADMIN,)

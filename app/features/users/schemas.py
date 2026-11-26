import re
import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.roles import Role

_PHONE_RE = re.compile(r"^\+?[0-9]{9,15}$")


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"[\s\-()]", "", value)
    if cleaned == "":
        return None
    if not _PHONE_RE.fullmatch(cleaned):
        raise ValueError("Phone must be 9-15 digits, optionally starting with +")
    return cleaned


Phone = Annotated[str | None, AfterValidator(_normalize_phone)]
Password = Annotated[str, Field(min_length=8, max_length=128)]
FullName = Annotated[str, Field(min_length=1, max_length=120)]


class UserCreate(BaseModel):
    email: EmailStr
    full_name: FullName
    phone: Phone = None
    role: Role
    password: Password


class UserUpdate(BaseModel):
    """All fields optional; only the fields sent are changed. Send `phone: null` to clear it."""

    full_name: FullName | None = None
    phone: Phone = None
    role: Role | None = None
    is_active: bool | None = None
    password: Password | None = None

    @model_validator(mode="after")
    def _no_null_for_required(self) -> Self:
        for name in ("full_name", "role", "is_active", "password"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    role: Role
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

"""Application settings, read from environment variables and `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"

    database_url: str = "postgresql+asyncpg://kulmax:kulmax@localhost:5432/kulmax"
    test_database_url: str = "postgresql+asyncpg://kulmax:kulmax@localhost:5432/kulmax_test"

    jwt_secret: str = "change-me"  # noqa: S105 - overridden by env; checked at startup
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000"]
    business_timezone: str = "Africa/Kigali"

    seed_admin_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

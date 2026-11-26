"""API entry point: `uvicorn app.main:app`."""

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.errors import AppError, ErrorResponse, register_error_handlers
from app.features.auth.router import router as auth_router
from app.features.dashboard.router import router as dashboard_router
from app.features.incidents.router import router as incidents_router
from app.features.notifications.router import router as notifications_router
from app.features.orders.router import router as orders_router
from app.features.readings.router import router as readings_router
from app.features.reports.router import router as reports_router
from app.features.sales.router import router as sales_router
from app.features.sensors.router import router as sensors_router
from app.features.users.router import router as users_router
from app.features.vehicles.router import router as vehicles_router

API_PREFIX = "/api/v1"

FEATURE_ROUTERS: tuple[APIRouter, ...] = (
    auth_router,
    users_router,
    vehicles_router,
    sensors_router,
    readings_router,
    incidents_router,
    notifications_router,
    orders_router,
    sales_router,
    reports_router,
    dashboard_router,
)


class HealthResponse(BaseModel):
    status: str
    database: str


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"


def _check_settings(settings: Settings) -> None:
    if settings.app_env == "production" and (
        settings.jwt_secret == "change-me" or len(settings.jwt_secret) < 32  # noqa: S105
    ):
        raise RuntimeError("JWT_SECRET must be set to a random value of 32+ chars in production")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    _check_settings(settings)

    app = FastAPI(
        title="Kulmax API",
        version="0.1.0",
        description="Orders, sales, cold-chain temperature monitoring and alerts for Kulmax.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
        responses={503: {"model": ErrorResponse}},
    )
    async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
        try:
            await session.execute(text("SELECT 1"))
        except Exception as exc:
            raise ServiceUnavailableError(
                "Database unavailable", code="database_unavailable"
            ) from exc
        return HealthResponse(status="ok", database="ok")

    for router in FEATURE_ROUTERS:
        app.include_router(router, prefix=API_PREFIX)

    return app


app = create_app()

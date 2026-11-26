from datetime import UTC, date, datetime

from httpx import AsyncClient

from app.core import events
from app.core.time import business_day_start_utc


async def test_health_checks_database(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_unknown_route_uses_error_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_cors_allows_configured_frontend_origin(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_openapi_has_feature_tags(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    tags = {tag for path in schema["paths"].values() for op in path.values() for tag in op["tags"]}
    assert {"auth", "users", "health"} <= tags


async def test_event_bus_delivers_to_subscribers() -> None:
    received: list[str] = []

    @events.subscribe("test.event")
    async def handler(payload: str) -> None:
        received.append(payload)

    try:
        await events.publish("test.event", "hello")
        await events.publish("other.event", "ignored")
    finally:
        events.clear_handlers()

    assert received == ["hello"]


def test_business_day_starts_at_kigali_midnight() -> None:
    # Kigali is UTC+2 with no DST.
    assert business_day_start_utc(date(2026, 1, 15)) == datetime(2026, 1, 14, 22, 0, tzinfo=UTC)

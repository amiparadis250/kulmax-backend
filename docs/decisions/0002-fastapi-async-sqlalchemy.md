# 0002. FastAPI with async SQLAlchemy 2.0 on PostgreSQL

Date: 2026-11-26 · Status: accepted

## Context
The API serves a Next.js frontend that will generate TypeScript types from OpenAPI. It also
receives sensor readings and makes outgoing HTTP calls (OpenWA, email API). The team works in
Python.

## Decision
FastAPI + Pydantic v2 for the HTTP layer (typed, OpenAPI out of the box). PostgreSQL with
SQLAlchemy 2.0 async (asyncpg) for data, Alembic for migrations, httpx for outgoing calls.
Times are stored as `timestamptz` in UTC.

## Consequences
- One async stack end to end; slow outgoing calls do not block other requests.
- Async SQLAlchemy needs care: no lazy loading in async code (load relationships explicitly),
  `expire_on_commit=False` on sessions.
- Tests run against a real Postgres database, not SQLite, so constraints and types match prod.

# Kulmax backend

FastAPI API for **Kulmax**, a transport company in Rwanda. Single business, no multi-tenancy.
Only Kulmax employees log in (browser, separate Next.js app). Customers and drivers have no accounts.

What it does: **orders** (transport requests), **sales** (money earned; never linked to orders),
**temperature monitoring** of ~10 cold-chain vehicles (sensors → GSM gateway → this API), and
**incidents + alerts** (high / low / offline) via WhatsApp (self-hosted OpenWA), email and dashboard.

## Stack
Python 3.13 + uv · FastAPI · Pydantic v2 · pydantic-settings · PostgreSQL (16+) · SQLAlchemy 2.0
async + asyncpg · Alembic · PyJWT · pwdlib (argon2) · httpx · APScheduler 3 (separate worker
process) · pytest + pytest-asyncio · ruff · mypy (strict on `app/`).
All times stored in UTC (`timestamptz`); business timezone `Africa/Kigali` (`core/time.py`).

## Layout (feature-based vertical slices)
```
app/main.py            create_app(): CORS, error handlers, /health, includes FEATURE_ROUTERS
app/worker.py          APScheduler process; auto-loads every features/*/jobs.py `register()`
app/core/              plumbing only, no business rules:
  config  db (Base, EntityMixin, get_session)  security (hash, JWT)  auth (get_current_user,
  require_roles, CurrentUser)  roles  errors  events  time  pagination
app/features/<name>/   models  schemas  repository  service  router  [dependencies] [jobs] [cli]
migrations/            Alembic (async); env.py auto-imports every features/*/models.py
tests/                 conftest.py (fixtures) + features/<name>/test_*.py
docs/specs/<name>.md   one spec per feature: the source of truth for behaviour
docs/decisions/        ADRs
```
Reference features to copy: **`users`** (CRUD, rules, CLI) and **`auth`** (no tables, uses
another feature's service).

## Feature rules
- A feature owns its tables. Other features **never** import its `repository.py`/`models.py` or
  query its tables. They call its `service.py` or subscribe to its events (`core/events.py`).
  Database foreign keys to another feature's table are fine (integrity); joins/queries are not.
- `repository.py` = queries only. `service.py` = business rules + transaction (services call
  `await session.commit()` on writes). `router.py` = thin: validate, check role, call service,
  return a schema.
- Every route declares roles: `Depends(require_roles(*ALL_ROLES | MANAGERS | ADMINS))`
  (`core/roles.py`). Public routes (login, refresh, health, device ingest) have a comment saying
  why. Permissions are enforced here, never only in the frontend.
- Models inherit `EntityMixin, Base` (UUID pk, `created_at`, `updated_at`). Enums are stored as
  strings with a CHECK constraint (`Enum(..., native_enum=False, create_constraint=True)`).
- Business errors raise `AppError` subclasses from `core/errors.py` with a specific `code`
  (`NotFoundError`, `ConflictError`, `BusinessRuleError`, `PermissionDeniedError`, ...).
- Jobs live in the worker, never in the API process. Run exactly one worker.
- Don't add features, tables or libraries that aren't in a spec without asking. If code and
  spec disagree: stop, ask, update the spec first, then the code.

## API conventions
- Prefix `/api/v1`, plural nouns (`/orders`, `/orders/{id}/status`). Tag = feature name.
- Every route has `response_model`; routers pass `responses=ERROR_RESPONSES` (OpenAPI is used to
  generate the frontend's TypeScript types, keep it clean).
- Errors: `{"error": {"code": "...", "message": "...", "details": {...}}}`. Request validation
  → 422 `validation_error`; business rule → 422 with a specific code; 401/403/404/409 as usual.
- Lists: `params: PageParams = Depends(page_params)` (`page` ≥1, `limit` 1–100, default 20) and
  return `Page[T]` = `{items, total, page, limit}`; filters are query params.
- PATCH bodies: only fields sent are changed (`model_dump(exclude_unset=True)`).
- `GET /health` (no auth) checks the DB.

## Commands (Windows-friendly; no make)
```
uv sync                                   # install
cp .env.example .env                      # then edit DATABASE_URL, TEST_DATABASE_URL, JWT_SECRET
uv run python tasks.py createdb           # create the dev database if missing
uv run python tasks.py migrate            # alembic upgrade head
uv run python tasks.py makemigration "add vehicles"   # autogenerate; always review the file
uv run python tasks.py seed-admin --email admin@kulmax.rw --full-name "Admin"
uv run python tasks.py dev                # API on :8000, docs at /docs
uv run python tasks.py worker             # scheduled jobs
uv run python tasks.py test               # pytest (wipes + migrates TEST_DATABASE_URL, must end _test)
uv run python tasks.py lint               # ruff check + format check + mypy
uv run python tasks.py format
```
Tests: real Postgres; each test runs in a rolled-back transaction. Fixtures: `client`,
`session`, `make_user(role, ...)`, `admin`/`manager`/`staff`, `auth_headers(user)`.

## How to add a feature
1. Read `docs/specs/<feature>.md` (+ specs it depends on). Resolve open questions first.
2. Models in `models.py` → `tasks.py makemigration` → review and edit the migration.
3. `repository.py` (queries) → `service.py` (rules, commits, events) → `schemas.py` → `router.py`.
4. Jobs in `jobs.py` with `register(scheduler)`; event handlers imported in the feature `__init__`.
5. Tests in `tests/features/<feature>/` covering every acceptance criterion and every role.
6. `tasks.py lint` and `tasks.py test` pass.
7. Spec → `Status: implemented`, tick criteria. Update the feature list below.

## Features
| Feature | Status |
|---|---|
| auth, users | implemented |
| vehicles, sensors, readings, incidents, notifications, orders, sales, reports, dashboard | spec draft, skeleton only |

Suggested build order: vehicles → sensors → readings → incidents → notifications → orders →
sales → dashboard → reports.

## Deployment target
Hostinger VPS (Linux) running Docker Compose: reverse proxy (HTTPS) → api + frontend;
worker, db and openwa on the internal network only. OpenWA uses a dedicated SIM/number.

## Deferred (decided to postpone)
- Docker / Docker Compose (`api`, `worker`, `db`, `openwa` with `rmyndharis/openwa`,
  `ENGINE_TYPE=baileys`, `AUTO_START_SESSIONS=true`, `./data` volume, not public). Local dev
  currently uses a locally installed PostgreSQL.
- Email provider and OpenWA configuration (built with the `notifications` feature).

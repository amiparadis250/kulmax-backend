# 0001. Organise the code by feature (vertical slices)

Date: 2026-11-26 · Status: accepted

## Context
The app has about 11 business areas (orders, sales, sensors, incidents, ...) that will be built one
at a time, often in separate sessions. A layer-first layout (`models/`, `routers/`, `services/`)
spreads one feature across many folders and makes it easy for features to reach into each
other's tables.

## Decision
Each feature is a package under `app/features/<name>/` with its own `models`, `schemas`,
`repository`, `service`, `router` and optional `jobs`. Shared plumbing only lives in `app/core/`.
A feature owns its tables; other features use only its `service.py` or its events.
Each feature has a spec in `docs/specs/<name>.md`.

## Consequences
- Building or changing a feature touches one folder + its tests + its spec.
- Cross-feature reads go through service functions, which costs a little extra code
  (e.g. reports cannot just join every table) but keeps the boundaries clear.
- Alembic and the worker discover feature modules automatically, so adding a feature never
  means editing a central registry (except the router list in `main.py`).

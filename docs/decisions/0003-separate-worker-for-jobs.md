# 0003. Run scheduled jobs in a separate worker process

Date: 2026-11-26 · Status: accepted

## Context
Several things run on a timer: the offline-sensor check (every minute), incident reminders
(every 30 minutes, max 3), and the WhatsApp send queue (messages a few seconds apart). If the
scheduler ran inside the API, every Uvicorn worker would run every job, sending duplicate
alerts.

## Decision
APScheduler 3 (`AsyncIOScheduler`) runs in its own process, `python -m app.worker`. Each feature
can provide `jobs.py` with `register(scheduler)`; the worker loads them automatically. Exactly one
worker process is deployed.

## Consequences
- The API can scale to many workers safely.
- Work the API wants done "later" (e.g. a WhatsApp message) is written to a table that the
  worker processes, not handed over in memory. The table is the queue.
- Jobs must be idempotent and safe if the worker restarts mid-run.
- Deployment has two long-running processes (`api`, `worker`).

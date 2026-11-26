"""Scheduled jobs for `notifications`, run by the worker process (app/worker.py)."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler


def register(scheduler: AsyncIOScheduler) -> None:
    """Add this feature's jobs to the scheduler.

    Not implemented yet. See docs/specs/notifications.md.
    """

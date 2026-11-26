"""Worker process for scheduled jobs: `python -m app.worker`.

Runs separately from the API so jobs never run twice when the API has several Uvicorn
workers. Run exactly ONE worker process. Every feature with a `jobs.py` exposing
`register(scheduler)` is picked up automatically.
"""

import asyncio
import logging
import signal
from contextlib import suppress

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.db import get_engine
from app.features import import_feature_modules

logger = logging.getLogger("kulmax.worker")


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    for module in import_feature_modules("jobs"):
        register = getattr(module, "register", None)
        if callable(register):
            register(scheduler)
            logger.info("Registered jobs from %s", module.__name__)
    return scheduler


async def run() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Worker started with %d job(s)", len(scheduler.get_jobs()))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):  # not supported on Windows; Ctrl+C still works
            loop.add_signal_handler(sig, stop.set)
    try:
        await stop.wait()
    finally:
        scheduler.shutdown(wait=True)
        await get_engine().dispose()
        logger.info("Worker stopped")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    with suppress(KeyboardInterrupt):
        asyncio.run(run())


if __name__ == "__main__":
    main()

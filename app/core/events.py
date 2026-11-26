"""Tiny in-process event bus so features can react to each other without importing internals.

Usage:
    @subscribe("reading.recorded")
    async def on_reading(event: ReadingRecorded) -> None: ...

    await publish("reading.recorded", ReadingRecorded(...))

Handlers run in order, awaited, in the publisher's process. Events are not persisted;
anything that must survive a crash belongs in a table, not only in an event.
Handlers are registered when their module is imported, so each feature imports its
subscribers in its `__init__.py`.
"""

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[[Any], Awaitable[None]]

_handlers: dict[str, list[Handler]] = defaultdict(list)


def subscribe(event_name: str) -> Callable[[Handler], Handler]:
    def decorator(handler: Handler) -> Handler:
        if handler not in _handlers[event_name]:
            _handlers[event_name].append(handler)
        return handler

    return decorator


async def publish(event_name: str, payload: Any) -> None:
    for handler in list(_handlers[event_name]):
        await handler(payload)


def clear_handlers() -> None:
    """For tests only."""
    _handlers.clear()

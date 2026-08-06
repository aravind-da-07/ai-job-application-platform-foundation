"""
Lightweight in-process event bus.

Future modules (Resume Parser, Job Discovery, AI Matching, Automation,
Notifications, Dashboard) should publish and subscribe to events here
instead of importing and calling each other directly. This keeps the
system loosely coupled: e.g. the Notification module can subscribe to
`EventType.CAPTCHA_DETECTED` without the Automation module knowing the
Notification module exists.

This is intentionally a synchronous, in-memory bus for a single-process
deployment. The publish/subscribe interface is designed so it can be
swapped for a real message queue (e.g. Redis Streams, SQS) later without
changing any calling code — only this module's internals would change.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, DefaultDict

from src.shared.config.constants import EventType
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    def __init__(self) -> None:
        self._subscribers: DefaultDict[EventType, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)
        logger.debug("Handler {} subscribed to {}", getattr(handler, "__name__", handler), event_type)

    def publish(self, event: Event) -> None:
        logger.info("Event published: {}", event.type.value, extra={"payload": event.payload})
        for handler in self._subscribers.get(event.type, []):
            try:
                handler(event)
            except Exception:
                # A failing subscriber must never break the publisher or
                # other subscribers.
                logger.exception(
                    "Event handler {} failed for event {}",
                    getattr(handler, "__name__", handler),
                    event.type,
                )

    def clear(self) -> None:
        """Removes all subscriptions. Intended for use in tests."""
        self._subscribers.clear()


_event_bus = EventBus()


def get_event_bus() -> EventBus:
    return _event_bus

from __future__ import annotations

from src.shared.config.constants import EventType
from src.shared.events.event_bus import Event, EventBus


def test_publish_calls_subscribed_handler() -> None:
    bus = EventBus()
    received = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.JOB_DISCOVERED, handler)
    bus.publish(Event(type=EventType.JOB_DISCOVERED, payload={"job_id": "123"}))

    assert len(received) == 1
    assert received[0].payload == {"job_id": "123"}


def test_publish_does_not_call_unrelated_handlers() -> None:
    bus = EventBus()
    received = []
    bus.subscribe(EventType.JOB_DISCOVERED, lambda e: received.append(e))
    bus.publish(Event(type=EventType.CAPTCHA_DETECTED))
    assert received == []


def test_failing_handler_does_not_break_other_handlers() -> None:
    bus = EventBus()
    calls = []

    def bad_handler(event: Event) -> None:
        raise RuntimeError("boom")

    def good_handler(event: Event) -> None:
        calls.append(event)

    bus.subscribe(EventType.APPLICATION_SUBMITTED, bad_handler)
    bus.subscribe(EventType.APPLICATION_SUBMITTED, good_handler)
    bus.publish(Event(type=EventType.APPLICATION_SUBMITTED))

    assert len(calls) == 1


def test_clear_removes_subscriptions() -> None:
    bus = EventBus()
    received = []
    bus.subscribe(EventType.NOTIFICATION_SENT, lambda e: received.append(e))
    bus.clear()
    bus.publish(Event(type=EventType.NOTIFICATION_SENT))
    assert received == []

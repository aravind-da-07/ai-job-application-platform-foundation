"""Date/time utilities. All platform timestamps are UTC and timezone-aware."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """The canonical 'current time' for the platform. Never use naive datetimes."""
    return datetime.now(timezone.utc)


def to_iso8601(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

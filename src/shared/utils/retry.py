"""
Reusable retry decorator with exponential backoff.

Used by any module making an unreliable external call (Supabase, AI
providers, job-source APIs, browser navigation). Configurable per call
site; falls back to platform defaults from settings.
"""

from __future__ import annotations

import functools
import time
from typing import Callable, ParamSpec, TypeVar

from src.shared.config.settings import get_settings
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def retry_with_backoff(
    *,
    max_attempts: int | None = None,
    base_delay_seconds: int | None = None,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Retries the decorated function on the given exception types using
    exponential backoff (base_delay * 2^attempt).

    Defaults come from settings.default_retry_count /
    default_retry_backoff_seconds when not explicitly provided.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            settings = get_settings()
            attempts = max_attempts or settings.default_retry_count
            delay = base_delay_seconds or settings.default_retry_backoff_seconds

            last_exception: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001
                    last_exception = exc
                    if attempt == attempts:
                        logger.error(
                            "{} failed after {} attempts: {}", func.__name__, attempts, exc
                        )
                        raise
                    wait_time = delay * (2 ** (attempt - 1))
                    logger.warning(
                        "{} failed on attempt {}/{} ({}). Retrying in {}s",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                        wait_time,
                    )
                    time.sleep(wait_time)
            # Unreachable, but keeps type checkers satisfied.
            assert last_exception is not None
            raise last_exception

        return wrapper

    return decorator

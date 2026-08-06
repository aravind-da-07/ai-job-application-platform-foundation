"""
Structured logging configuration using Loguru.

Every module should obtain a logger via `get_logger(__name__)` rather
than constructing its own. This guarantees consistent formatting,
rotation, and (optionally) forwarding of important events to Supabase.

Loguru's default handler is removed and replaced with:
  1. A colorized console sink (human-readable, for local dev)
  2. A rotating file sink (JSON-serialized, for durable local logs)

A third, optional Supabase sink is registered by
`src.shared.logging.supabase_sink` when `log_to_supabase` is enabled;
it is kept separate so this module has no database dependency.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger as _logger

from src.shared.config.settings import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotently configure the global Loguru logger from settings."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    _logger.remove()

    _logger.add(
        sys.stderr,
        level=settings.log_level.value,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[module]}</cyan> | "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=not settings.is_production,
    )

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    _logger.add(
        log_dir / "platform_{time:YYYY-MM-DD}.log",
        level=settings.log_level.value,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        serialize=True,
        enqueue=True,
        backtrace=False,
        diagnose=not settings.is_production,
    )

    _logger.configure(extra={"module": "platform"})
    _CONFIGURED = True


def get_logger(module_name: str):
    """
    Returns a Loguru logger bound with the calling module's name so log
    lines are attributable at a glance.

    Example:
        from src.shared.logging.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Resume parsed successfully", extra={"candidate_id": cid})
    """
    configure_logging()
    return _logger.bind(module=module_name)

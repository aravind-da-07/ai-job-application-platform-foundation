"""
Scheduler infrastructure built on APScheduler.

This module ONLY provides infrastructure: starting/stopping the
scheduler, registering jobs (interval or cron), and centralized
failure logging. It contains no business jobs itself — future modules
(Job Discovery, Analytics, Cleanup) will call
`SchedulerManager.add_interval_job(...)` / `add_cron_job(...)` to
register their own work.
"""

from __future__ import annotations

from typing import Any, Callable

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler

from src.shared.config.settings import get_settings
from src.shared.core.exceptions import SchedulerError
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


class SchedulerManager:
    """Thin, testable wrapper around an APScheduler BackgroundScheduler."""

    def __init__(self) -> None:
        settings = get_settings()
        self._scheduler = BackgroundScheduler(
            timezone=settings.scheduler_timezone,
            job_defaults={
                "max_instances": settings.scheduler_job_defaults_max_instances,
                "misfire_grace_time": settings.scheduler_misfire_grace_time_seconds,
                "coalesce": True,
            },
        )
        self._scheduler.add_listener(
            self._on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

    def _on_job_event(self, event: Any) -> None:
        if event.code == EVENT_JOB_ERROR:
            logger.error(
                "Scheduled job {} raised an exception: {}", event.job_id, event.exception
            )
        elif event.code == EVENT_JOB_MISSED:
            logger.warning("Scheduled job {} was missed (scheduled_run_time={})", event.job_id, event.scheduled_run_time)
        else:
            logger.debug("Scheduled job {} executed successfully", event.job_id)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler shut down gracefully")

    def add_interval_job(
        self,
        func: Callable[..., Any],
        *,
        job_id: str,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        replace_existing: bool = True,
        **trigger_kwargs: Any,
    ) -> None:
        if seconds == 0 and minutes == 0 and hours == 0:
            raise SchedulerError(f"Interval job '{job_id}' requires a non-zero interval")
        self._scheduler.add_job(
            func,
            trigger="interval",
            seconds=seconds or 0,
            minutes=minutes or 0,
            hours=hours or 0,
            id=job_id,
            replace_existing=replace_existing,
            **trigger_kwargs,
        )
        logger.info("Registered interval job '{}'", job_id)

    def add_cron_job(
        self,
        func: Callable[..., Any],
        *,
        job_id: str,
        replace_existing: bool = True,
        **cron_kwargs: Any,
    ) -> None:
        """`cron_kwargs` accepts APScheduler CronTrigger fields, e.g. hour=9, minute=0."""
        self._scheduler.add_job(
            func,
            trigger="cron",
            id=job_id,
            replace_existing=replace_existing,
            **cron_kwargs,
        )
        logger.info("Registered cron job '{}' ({})", job_id, cron_kwargs)

    def remove_job(self, job_id: str) -> None:
        self._scheduler.remove_job(job_id)
        logger.info("Removed job '{}'", job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        return [
            {"id": job.id, "next_run_time": str(job.next_run_time), "trigger": str(job.trigger)}
            for job in self._scheduler.get_jobs()
        ]

    @property
    def running(self) -> bool:
        return self._scheduler.running


_scheduler_manager: SchedulerManager | None = None


def get_scheduler_manager() -> SchedulerManager:
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager

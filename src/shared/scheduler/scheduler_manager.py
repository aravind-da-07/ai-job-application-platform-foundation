"""
Scheduler infrastructure built on APScheduler.

This module ONLY provides infrastructure:
- starting/stopping the scheduler
- registering interval jobs
- registering cron jobs
- removing jobs
- listing jobs
- centralized scheduler failure logging

Business workflows are owned by higher-level modules.
"""

from __future__ import annotations

from typing import Any, Callable

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
)
from apscheduler.schedulers.background import BackgroundScheduler

from src.shared.config.settings import get_settings
from src.shared.core.exceptions import SchedulerError
from src.shared.logging.logger import get_logger


logger = get_logger(__name__)


class SchedulerManager:
    """
    Thin, testable wrapper around APScheduler BackgroundScheduler.
    """

    def __init__(self) -> None:
        settings = get_settings()

        self._scheduler = BackgroundScheduler(
            timezone=settings.scheduler_timezone,
            job_defaults={
                "max_instances": (
                    settings.scheduler_job_defaults_max_instances
                ),
                "misfire_grace_time": (
                    settings.scheduler_misfire_grace_time_seconds
                ),
                "coalesce": True,
            },
        )

        self._scheduler.add_listener(
            self._on_job_event,
            EVENT_JOB_EXECUTED
            | EVENT_JOB_ERROR
            | EVENT_JOB_MISSED,
        )

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _on_job_event(self, event: Any) -> None:
        """
        Handle APScheduler execution events.
        """

        if event.code == EVENT_JOB_ERROR:
            logger.error(
                "Scheduled job {} raised an exception: {}",
                event.job_id,
                event.exception,
            )

        elif event.code == EVENT_JOB_MISSED:
            logger.warning(
                "Scheduled job {} was missed "
                "(scheduled_run_time={})",
                event.job_id,
                event.scheduled_run_time,
            )

        else:
            logger.debug(
                "Scheduled job {} executed successfully",
                event.job_id,
            )

    # ------------------------------------------------------------------
    # Scheduler lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Start the scheduler if it is not already running.
        """

        if not self._scheduler.running:
            self._scheduler.start()

            logger.info(
                "Scheduler started"
            )

    def shutdown(
        self,
        wait: bool = True,
    ) -> None:
        """
        Shut down the scheduler gracefully.
        """

        if self._scheduler.running:
            self._scheduler.shutdown(
                wait=wait
            )

            logger.info(
                "Scheduler shut down gracefully"
            )

    # ------------------------------------------------------------------
    # Job registration
    # ------------------------------------------------------------------

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
        """
        Register a recurring interval job.
        """

        if seconds == 0 and minutes == 0 and hours == 0:
            raise SchedulerError(
                f"Interval job '{job_id}' requires "
                "a non-zero interval."
            )

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

        logger.info(
            "Registered interval job '{}'",
            job_id,
        )

    def add_cron_job(
        self,
        func: Callable[..., Any],
        *,
        job_id: str,
        replace_existing: bool = True,
        **cron_kwargs: Any,
    ) -> None:
        """
        Register a cron-based scheduled job.

        Example:

            hour=9,
            minute=0
        """

        self._scheduler.add_job(
            func,
            trigger="cron",
            id=job_id,
            replace_existing=replace_existing,
            **cron_kwargs,
        )

        logger.info(
            "Registered cron job '{}' ({})",
            job_id,
            cron_kwargs,
        )

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def remove_job(
        self,
        job_id: str,
    ) -> None:
        """
        Remove a scheduled job.
        """

        self._scheduler.remove_job(
            job_id
        )

        logger.info(
            "Removed job '{}'",
            job_id,
        )

    def list_jobs(self) -> list[dict[str, Any]]:
        """
        Return a serializable representation of registered jobs.

        APScheduler's Job API can differ between versions, so we use
        safe attribute access instead of assuming every Job object
        exposes every property.
        """

        jobs: list[dict[str, Any]] = []

        for job in self._scheduler.get_jobs():
            next_run_time = getattr(
                job,
                "next_run_time",
                None,
            )

            jobs.append(
                {
                    "id": job.id,
                    "next_run_time": str(
                        next_run_time
                    ),
                    "trigger": str(
                        job.trigger
                    ),
                }
            )

        return jobs

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        """
        Return whether the scheduler is running.
        """

        return self._scheduler.running


# ----------------------------------------------------------------------
# Global scheduler manager
# ----------------------------------------------------------------------

_scheduler_manager: SchedulerManager | None = None


def get_scheduler_manager() -> SchedulerManager:
    """
    Return the application-wide SchedulerManager singleton.
    """

    global _scheduler_manager

    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()

    return _scheduler_manager
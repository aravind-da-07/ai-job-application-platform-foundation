"""
Automation scheduler integration.

Connects SchedulerManager with AutomationOrchestrator.

SchedulerManager remains generic infrastructure.

Each scheduled execution creates its own database session and
automation service so APScheduler background threads never reuse
a SQLAlchemy Session owned by another thread or request.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.modules.automation.infrastructure.repositories.automation_repository_impl import (
    SQLAlchemyAutomationRepository,
)
from src.modules.automation.services.automation_orchestrator import (
    AutomationOrchestrator,
)
from src.modules.automation.services.automation_service import (
    AutomationService,
)
from src.shared.database.session import session_scope
from src.shared.logging.logger import get_logger
from src.shared.scheduler.scheduler_manager import (
    SchedulerManager,
    get_scheduler_manager,
)


logger = get_logger(__name__)


class AutomationScheduler:
    """
    Registers automation workflows with APScheduler.

    This class does not contain workflow business logic.

    It only connects scheduled triggers to the orchestrator.

    IMPORTANT:
    Every scheduled execution creates a fresh SQLAlchemy Session.
    SQLAlchemy Sessions must never be shared between APScheduler
    worker threads.
    """

    def __init__(
        self,
        orchestrator: AutomationOrchestrator,
        scheduler: SchedulerManager | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.scheduler = (
            scheduler or get_scheduler_manager()
        )

    # ------------------------------------------------------------------
    # Internal execution helper
    # ------------------------------------------------------------------

    def _execute_isolated(
        self,
        *,
        run_type: str,
        user_id: UUID | None,
        metadata: dict[str, Any] | None,
    ) -> None:
        """
        Execute one scheduled workflow using a completely fresh
        database session.

        The workflow definition is kept in the scheduler's
        orchestrator, while the persistence layer is recreated
        for this execution.
        """

        workflow = self.orchestrator.get_workflow(
            run_type
        )

        with session_scope() as session:
            repository = SQLAlchemyAutomationRepository(
                session
            )

            automation_service = AutomationService(
                repository
            )

            execution_orchestrator = (
                AutomationOrchestrator(
                    automation_service
                )
            )

            execution_orchestrator.register_workflow(
                run_type=workflow.run_type,
                handler=workflow.handler,
            )

            execution_orchestrator.execute(
                run_type=run_type,
                user_id=user_id,
                metadata=dict(metadata or {}),
            )

    # ------------------------------------------------------------------
    # Interval scheduling
    # ------------------------------------------------------------------

    def add_interval_workflow(
        self,
        *,
        job_id: str,
        run_type: str,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        replace_existing: bool = True,
    ) -> None:
        """
        Schedule an automation workflow using an interval trigger.
        """

        if not self.orchestrator.has_workflow(
            run_type
        ):
            raise ValueError(
                f"Automation workflow '{run_type}' "
                "is not registered."
            )

        if (
            seconds == 0
            and minutes == 0
            and hours == 0
        ):
            raise ValueError(
                "Interval workflow requires "
                "a non-zero interval."
            )

        def scheduled_job() -> None:
            logger.info(
                "Executing scheduled automation job '{}'.",
                job_id,
            )

            try:
                self._execute_isolated(
                    run_type=run_type,
                    user_id=user_id,
                    metadata=metadata,
                )
            except Exception:
                logger.exception(
                    "Scheduled automation job '{}' failed.",
                    job_id,
                )

        self.scheduler.add_interval_job(
            scheduled_job,
            job_id=job_id,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            replace_existing=replace_existing,
        )

        logger.info(
            "Automation workflow '{}' scheduled as '{}'.",
            run_type,
            job_id,
        )

    # ------------------------------------------------------------------
    # Cron scheduling
    # ------------------------------------------------------------------

    def add_cron_workflow(
        self,
        *,
        job_id: str,
        run_type: str,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        replace_existing: bool = True,
        **cron_kwargs: Any,
    ) -> None:
        """
        Schedule an automation workflow using a cron trigger.

        Example:

            hour=9,
            minute=0
        """

        if not self.orchestrator.has_workflow(
            run_type
        ):
            raise ValueError(
                f"Automation workflow '{run_type}' "
                "is not registered."
            )

        def scheduled_job() -> None:
            logger.info(
                "Executing scheduled automation job '{}'.",
                job_id,
            )

            try:
                self._execute_isolated(
                    run_type=run_type,
                    user_id=user_id,
                    metadata=metadata,
                )
            except Exception:
                logger.exception(
                    "Scheduled automation job '{}' failed.",
                    job_id,
                )

        self.scheduler.add_cron_job(
            scheduled_job,
            job_id=job_id,
            replace_existing=replace_existing,
            **cron_kwargs,
        )

        logger.info(
            "Automation workflow '{}' scheduled as '{}'.",
            run_type,
            job_id,
        )

    # ------------------------------------------------------------------
    # Scheduler lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Start the underlying scheduler.
        """

        self.scheduler.start()

    def shutdown(
        self,
        *,
        wait: bool = True,
    ) -> None:
        """
        Shut down the underlying scheduler.
        """

        self.scheduler.shutdown(
            wait=wait
        )

    def remove_job(
        self,
        job_id: str,
    ) -> None:
        """
        Remove a scheduled automation job.
        """

        self.scheduler.remove_job(
            job_id
        )

    def list_jobs(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return currently registered scheduled jobs.
        """

        return self.scheduler.list_jobs()

    @property
    def running(self) -> bool:
        """
        Return whether the scheduler is currently running.
        """

        return self.scheduler.running
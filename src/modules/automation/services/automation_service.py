"""
Automation service.

This service coordinates automation-run lifecycle management and
persistent audit logging.

Business workflows such as job discovery, AI matching and application
automation should use this service instead of directly manipulating
automation database records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.modules.automation.domain.entities.automation import (
    AutomationLog,
    AutomationLogLevel,
    AutomationRun,
    AutomationRunStatus,
)
from src.modules.automation.domain.repositories.automation_repository import (
    AutomationRepository,
)


class AutomationService:
    """
    Application service responsible for automation lifecycle management.

    Responsibilities:

    - Start automation runs.
    - Transition run states.
    - Persist audit logs.
    - Track processed/succeeded/failed items.
    - Complete runs successfully.
    - Fail runs safely with error information.
    """

    def __init__(self, repository: AutomationRepository) -> None:
        self.repository = repository

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def start_run(
        self,
        *,
        run_type: str,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AutomationRun:
        """
        Create and immediately start an automation run.
        """

        if not run_type.strip():
            raise ValueError("run_type cannot be empty.")

        run = AutomationRun(
            user_id=user_id,
            run_type=run_type,
            status=AutomationRunStatus.QUEUED,
            metadata=metadata or {},
        )

        created_run = self.repository.create_run(run)

        started_run = self.repository.update_run_status(
            created_run.id,
            AutomationRunStatus.IN_PROGRESS,
        )

        self.log(
            run_id=started_run.id,
            event_type="run_started",
            message=f"Automation run '{run_type}' started.",
            level=AutomationLogLevel.INFO,
            entity_type="automation_run",
            entity_id=started_run.id,
            status=started_run.status.value,
            metadata={
                "run_type": run_type,
            },
        )

        return started_run

    def get_run(
        self,
        run_id: UUID,
    ) -> AutomationRun | None:
        """Return an automation run by ID."""

        return self.repository.get_run_by_id(run_id)

    def complete_run(
        self,
        run_id: UUID,
        *,
        items_processed: int | None = None,
        items_succeeded: int | None = None,
        items_failed: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AutomationRun:
        """
        Mark an automation run as completed successfully.
        """

        current_run = self._require_run(run_id)

        processed = (
            current_run.items_processed
            if items_processed is None
            else items_processed
        )

        succeeded = (
            current_run.items_succeeded
            if items_succeeded is None
            else items_succeeded
        )

        failed = (
            current_run.items_failed
            if items_failed is None
            else items_failed
        )

        self._validate_counters(
            processed=processed,
            succeeded=succeeded,
            failed=failed,
        )

        updated_metadata = dict(current_run.metadata)

        if metadata:
            updated_metadata.update(metadata)

        now = datetime.now(timezone.utc)

        completed_run = current_run.model_copy(
            update={
                "status": AutomationRunStatus.COMPLETED,
                "completed_at": now,
                "items_processed": processed,
                "items_succeeded": succeeded,
                "items_failed": failed,
                "metadata": updated_metadata,
                "updated_at": now,
            }
        )

        saved_run = self.repository.update_run(completed_run)

        self.log(
            run_id=saved_run.id,
            event_type="run_completed",
            message=(
                f"Automation run '{saved_run.run_type}' "
                "completed successfully."
            ),
            level=AutomationLogLevel.INFO,
            entity_type="automation_run",
            entity_id=saved_run.id,
            status=saved_run.status.value,
            metadata={
                "items_processed": saved_run.items_processed,
                "items_succeeded": saved_run.items_succeeded,
                "items_failed": saved_run.items_failed,
            },
        )

        return saved_run

    def fail_run(
        self,
        run_id: UUID,
        *,
        error_message: str,
        error_code: str | None = None,
        items_processed: int | None = None,
        items_succeeded: int | None = None,
        items_failed: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AutomationRun:
        """
        Mark an automation run as failed and persist the failure details.
        """

        if not error_message.strip():
            raise ValueError("error_message cannot be empty.")

        current_run = self._require_run(run_id)

        processed = (
            current_run.items_processed
            if items_processed is None
            else items_processed
        )

        succeeded = (
            current_run.items_succeeded
            if items_succeeded is None
            else items_succeeded
        )

        failed = (
            current_run.items_failed
            if items_failed is None
            else items_failed
        )

        self._validate_counters(
            processed=processed,
            succeeded=succeeded,
            failed=failed,
        )

        updated_metadata = dict(current_run.metadata)

        if metadata:
            updated_metadata.update(metadata)

        now = datetime.now(timezone.utc)

        failed_run = current_run.model_copy(
            update={
                "status": AutomationRunStatus.FAILED,
                "completed_at": now,
                "items_processed": processed,
                "items_succeeded": succeeded,
                "items_failed": failed,
                "error_message": error_message,
                "metadata": updated_metadata,
                "updated_at": now,
            }
        )

        saved_run = self.repository.update_run(failed_run)

        self.log(
            run_id=saved_run.id,
            event_type="run_failed",
            message=(
                f"Automation run '{saved_run.run_type}' failed: "
                f"{error_message}"
            ),
            level=AutomationLogLevel.ERROR,
            entity_type="automation_run",
            entity_id=saved_run.id,
            status=saved_run.status.value,
            error_code=error_code,
            metadata={
                "items_processed": saved_run.items_processed,
                "items_succeeded": saved_run.items_succeeded,
                "items_failed": saved_run.items_failed,
            },
        )

        return saved_run

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------

    def record_success(
        self,
        run_id: UUID,
        *,
        count: int = 1,
    ) -> AutomationRun:
        """
        Increment processed and successful counters.
        """

        self._validate_increment(count)

        current_run = self._require_run(run_id)

        updated_run = current_run.model_copy(
            update={
                "items_processed": (
                    current_run.items_processed + count
                ),
                "items_succeeded": (
                    current_run.items_succeeded + count
                ),
                "updated_at": datetime.now(timezone.utc),
            }
        )

        return self.repository.update_run(updated_run)

    def record_failure(
        self,
        run_id: UUID,
        *,
        count: int = 1,
        error_message: str | None = None,
        error_code: str | None = None,
    ) -> AutomationRun:
        """
        Increment processed and failed counters.

        An optional persistent error log is also created.
        """

        self._validate_increment(count)

        current_run = self._require_run(run_id)

        updated_run = current_run.model_copy(
            update={
                "items_processed": (
                    current_run.items_processed + count
                ),
                "items_failed": (
                    current_run.items_failed + count
                ),
                "updated_at": datetime.now(timezone.utc),
            }
        )

        saved_run = self.repository.update_run(updated_run)

        if error_message:
            self.log(
                run_id=run_id,
                event_type="item_failed",
                message=error_message,
                level=AutomationLogLevel.ERROR,
                entity_type="automation_run",
                entity_id=run_id,
                status=saved_run.status.value,
                error_code=error_code,
            )

        return saved_run

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(
        self,
        *,
        run_id: UUID,
        event_type: str,
        message: str,
        level: AutomationLogLevel = AutomationLogLevel.INFO,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        status: str | None = None,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AutomationLog:
        """
        Persist one automation audit event.
        """

        if not event_type.strip():
            raise ValueError("event_type cannot be empty.")

        if not message.strip():
            raise ValueError("message cannot be empty.")

        self._require_run(run_id)

        log_entry = AutomationLog(
            run_id=run_id,
            level=level,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            message=message,
            error_code=error_code,
            metadata=metadata or {},
        )

        return self.repository.create_log(log_entry)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_logs(
        self,
        run_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AutomationLog]:
        """Return audit logs for an automation run."""

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")

        self._require_run(run_id)

        return self.repository.list_logs(
            run_id,
            limit=limit,
            offset=offset,
        )

    def count_logs(
        self,
        run_id: UUID,
    ) -> int:
        """Return total audit logs for a run."""

        self._require_run(run_id)

        return self.repository.count_logs(run_id)

    # ------------------------------------------------------------------
    # Internal validation helpers
    # ------------------------------------------------------------------

    def _require_run(
        self,
        run_id: UUID,
    ) -> AutomationRun:
        run = self.repository.get_run_by_id(run_id)

        if run is None:
            raise ValueError(
                f"Automation run '{run_id}' was not found."
            )

        return run

    @staticmethod
    def _validate_increment(count: int) -> None:
        if count < 1:
            raise ValueError(
                "count must be greater than zero."
            )

    @staticmethod
    def _validate_counters(
        *,
        processed: int,
        succeeded: int,
        failed: int,
    ) -> None:
        if processed < 0 or succeeded < 0 or failed < 0:
            raise ValueError(
                "Automation item counters cannot be negative."
            )

        if succeeded + failed > processed:
            raise ValueError(
                "Succeeded and failed item counts cannot exceed "
                "the number of processed items."
            )
"""
Application Runner Coordinator.

This module connects the application queue, runner lifecycle,
application executor, and execution history layers.

Responsibilities:
    - Convert queued applications into runner requests.
    - Start the runner lifecycle.
    - Convert runner information into an execution request.
    - Invoke the configured application executor.
    - Translate execution results into runner states.
    - Persist normalized execution history.

This module intentionally contains NO:
    - Playwright
    - Selenium
    - browser selectors
    - LinkedIn-specific logic
    - SQLAlchemy
    - PostgreSQL
    - HTTP client logic
    - CAPTCHA bypass logic
    - authentication/MFA bypass logic
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionRequest,
    ApplicationExecutionResult,
    ApplicationExecutionStatus,
)
from src.modules.job_discovery.domain.application_executor.history import (
    ApplicationExecutionHistory,
    ApplicationExecutionHistoryStatus,
)
from src.modules.job_discovery.domain.application_queue import (
    ApplicationQueueItem,
)
from src.modules.job_discovery.domain.application_runner import (
    ApplicationRunRequest,
    ApplicationRunState,
)
from src.modules.job_discovery.services.application_executor.application_executor_service import (
    ApplicationExecutorService,
)
from src.modules.job_discovery.services.application_executor.history.history_service import (
    ApplicationExecutionHistoryService,
)
from src.modules.job_discovery.services.application_runner.application_runner_service import (
    ApplicationRunnerService,
)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ApplicationRunnerCoordinatorResult:
    """
    Normalized result returned after coordinating one application run.

    This object exposes both:
        - the current runner lifecycle state
        - the normalized execution result
        - the persisted history record, when history is configured
    """

    application_id: str
    external_job_id: str

    runner_state: ApplicationRunState

    execution_result: ApplicationExecutionResult

    history: ApplicationExecutionHistory | None = None

    history_recorded: bool = False

    metadata: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        if not self.external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        if self.metadata is None:
            object.__setattr__(
                self,
                "metadata",
                {},
            )


class ApplicationRunnerCoordinator:
    """
    Coordinates one complete application execution lifecycle.

    The coordinator is deliberately thin.

    It does not decide how a portal form works. The configured
    ApplicationExecutorService owns that responsibility through its
    executor port.
    """

    def __init__(
        self,
        *,
        runner_service: ApplicationRunnerService,
        executor_service: ApplicationExecutorService,
        history_service: ApplicationExecutionHistoryService | None = None,
    ) -> None:
        if runner_service is None:
            raise ValueError(
                "runner_service cannot be None."
            )

        if executor_service is None:
            raise ValueError(
                "executor_service cannot be None."
            )

        self._runner_service = runner_service
        self._executor_service = executor_service
        self._history_service = history_service

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def history_configured(self) -> bool:
        """Return whether execution history persistence is configured."""

        return self._history_service is not None

    @property
    def executor_configured(self) -> bool:
        """Return whether an application executor is configured."""

        return self._executor_service.executor_configured

    # ------------------------------------------------------------------
    # Public execution API
    # ------------------------------------------------------------------

    def run(
        self,
        queue_item: ApplicationQueueItem,
    ) -> ApplicationRunnerCoordinatorResult:
        """
        Execute one queued application through the complete lifecycle.

        Flow:

            QUEUED
                ↓
            IN_PROGRESS
                ↓
            ApplicationExecutorService
                ↓
            normalized result
                ↓
            runner terminal/intervention state
                ↓
            execution history
        """

        if queue_item is None:
            raise ValueError(
                "queue_item cannot be None."
            )

        request = self._build_runner_request(
            queue_item
        )

        registered_state = self._runner_service.register(
            request
        )

        if registered_state.status.value != "queued":
            raise ValueError(
                "Application is not in a runnable queued state. "
                f"Current status: {registered_state.status.value}"
            )

        running_state = self._runner_service.start(
            queue_item.application_id
        )

        execution_request = (
            self._build_execution_request(
                queue_item,
                running_state,
            )
        )

        execution_result = self._executor_service.execute(
            execution_request
        )

        final_state = self._apply_execution_result(
            queue_item,
            execution_result,
        )

        history = self._record_history(
            queue_item=queue_item,
            running_state=running_state,
            execution_result=execution_result,
            final_state=final_state,
        )

        return ApplicationRunnerCoordinatorResult(
            application_id=queue_item.application_id,
            external_job_id=queue_item.external_job_id,
            runner_state=final_state,
            execution_result=execution_result,
            history=history,
            history_recorded=history is not None,
            metadata={
                "executor_configured": (
                    self.executor_configured
                ),
                "history_configured": (
                    self.history_configured
                ),
            },
        )

    # ------------------------------------------------------------------
    # Request conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _build_runner_request(
        queue_item: ApplicationQueueItem,
    ) -> ApplicationRunRequest:
        """
        Convert a queue item into the runner's domain request.
        """

        return ApplicationRunRequest(
            application_id=queue_item.application_id,
            external_job_id=queue_item.external_job_id,
            job_url=queue_item.job_url,
            source=queue_item.source,
            attempt_number=(
                queue_item.attempt_count + 1
            ),
            maximum_attempts=queue_item.max_attempts,
            metadata=dict(queue_item.metadata),
        )

    @staticmethod
    def _build_execution_request(
        queue_item: ApplicationQueueItem,
        runner_state: ApplicationRunState,
    ) -> ApplicationExecutionRequest:
        """
        Convert a running application into an executor request.
        """

        metadata = dict(queue_item.metadata)

        metadata.update(
            {
                "attempt_number": (
                    runner_state.attempt_number
                ),
                "maximum_attempts": (
                    runner_state.maximum_attempts
                ),
            }
        )

        return ApplicationExecutionRequest(
            application_id=queue_item.application_id,
            external_job_id=queue_item.external_job_id,
            job_url=queue_item.job_url,
            source=queue_item.source,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Result translation
    # ------------------------------------------------------------------

    def _apply_execution_result(
        self,
        queue_item: ApplicationQueueItem,
        result: ApplicationExecutionResult,
    ) -> ApplicationRunState:
        """
        Translate the normalized executor result into runner state.
        """

        status = result.status

        if status == ApplicationExecutionStatus.SUBMITTED:
            return self._runner_service.mark_submitted(
                queue_item.application_id,
                reason=(
                    result.reason
                    or "Application submitted successfully."
                ),
                metadata=dict(result.metadata),
            )

        if status == ApplicationExecutionStatus.FAILED:
            return self._runner_service.mark_failed(
                queue_item.application_id,
                reason=(
                    result.reason
                    or "Application execution failed."
                ),
                error_code=result.error_code,
                metadata=dict(result.metadata),
            )

        if (
            status
            == ApplicationExecutionStatus.AUTHENTICATION_REQUIRED
        ):
            return self._runner_service.mark_authentication_required(
                queue_item.application_id,
                reason=(
                    result.reason
                    or "Authentication is required."
                ),
                metadata=dict(result.metadata),
            )

        if (
            status
            == ApplicationExecutionStatus.CAPTCHA_DETECTED
        ):
            return self._runner_service.mark_captcha_detected(
                queue_item.application_id,
                reason=(
                    result.reason
                    or "CAPTCHA detected."
                ),
                metadata=dict(result.metadata),
            )

        if (
            status
            == ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
        ):
            return self._runner_service.mark_manual_review_required(
                queue_item.application_id,
                reason=(
                    result.reason
                    or "Manual review is required."
                ),
                metadata=dict(result.metadata),
            )

        raise ValueError(
            "Unsupported application execution result status: "
            f"{status.value}"
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _record_history(
        self,
        *,
        queue_item: ApplicationQueueItem,
        running_state: ApplicationRunState,
        execution_result: ApplicationExecutionResult,
        final_state: ApplicationRunState,
    ) -> ApplicationExecutionHistory | None:
        """
        Convert the execution result into an immutable history record.

        History is optional at this stage because the repository can be
        configured later with durable persistence.
        """

        if self._history_service is None:
            return None

        started_at = (
            execution_result.started_at
            or running_state.started_at
            or utc_now()
        )

        completed_at = (
            execution_result.completed_at
            or final_state.completed_at
            or utc_now()
        )

        history_status = self._history_status(
            execution_result.status
        )

        confirmation_id = (
            execution_result.metadata.get(
                "confirmation_id"
            )
        )

        form_type = execution_result.metadata.get(
            "form_type"
        )

        history = ApplicationExecutionHistory(
            application_id=queue_item.application_id,
            external_job_id=queue_item.external_job_id,
            source=queue_item.source,
            status=history_status,
            started_at=started_at,
            completed_at=completed_at,
            form_type=form_type,
            fields_detected=(
                execution_result.fields_detected
            ),
            fields_filled=(
                execution_result.fields_filled
            ),
            confirmation_id=confirmation_id,
            manual_intervention_required=(
                execution_result.requires_manual_intervention
            ),
            reason=execution_result.reason,
            error_code=execution_result.error_code,
            metadata=dict(execution_result.metadata),
        )

        return self._history_service.record(
            history
        )

    @staticmethod
    def _history_status(
        status: ApplicationExecutionStatus,
    ) -> ApplicationExecutionHistoryStatus:
        """
        Translate execution status into the smaller history model.
        """

        if status == ApplicationExecutionStatus.SUBMITTED:
            return ApplicationExecutionHistoryStatus.SUBMITTED

        if status == ApplicationExecutionStatus.FAILED:
            return ApplicationExecutionHistoryStatus.FAILED

        if status in {
            ApplicationExecutionStatus.AUTHENTICATION_REQUIRED,
            ApplicationExecutionStatus.CAPTCHA_DETECTED,
            ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED,
        }:
            return (
                ApplicationExecutionHistoryStatus.MANUAL_REVIEW_REQUIRED
            )

        raise ValueError(
            "Execution status cannot be converted into "
            "terminal history: "
            f"{status.value}"
        )


__all__ = [
    "ApplicationRunnerCoordinator",
    "ApplicationRunnerCoordinatorResult",
]
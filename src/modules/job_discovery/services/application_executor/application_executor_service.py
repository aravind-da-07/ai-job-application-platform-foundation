"""
Application Executor Service.

Coordinates portal-independent application execution.

Portal-specific browser interaction belongs to infrastructure adapters.
"""

from __future__ import annotations

from typing import Protocol

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionContext,
    ApplicationExecutionRequest,
    ApplicationExecutionResult,
    ApplicationExecutionStatus,
)


class ApplicationExecutorPort(Protocol):
    """Contract implemented by a portal-specific executor."""

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:
        """Execute an application and return a normalized result."""
        ...


class ApplicationExecutorService:
    """Application execution orchestration service."""

    def __init__(
        self,
        executor: ApplicationExecutorPort | None = None,
    ) -> None:
        self._executor = executor

    @property
    def executor_configured(self) -> bool:
        """Return whether an executor is configured."""

        return self._executor is not None

    def configure_executor(
        self,
        executor: ApplicationExecutorPort,
    ) -> None:
        """Configure the portal-specific executor."""

        if executor is None:
            raise ValueError("executor cannot be None.")

        self._executor = executor

    @staticmethod
    def validate_request(
        request: ApplicationExecutionRequest,
    ) -> None:
        """Validate an application execution request."""

        if not request.application_id.strip():
            raise ValueError(
                "application_id cannot be empty."
            )

        if not request.external_job_id.strip():
            raise ValueError(
                "external_job_id cannot be empty."
            )

        if not request.job_url.strip():
            raise ValueError(
                "job_url cannot be empty."
            )

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:
        """
        Execute an application through the configured executor.

        Executor/runtime failures become normalized FAILED results.

        Identity mismatches are deliberately NOT swallowed because they
        represent a platform integrity violation.
        """

        self.validate_request(request)

        if self._executor is None:
            return ApplicationExecutionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                source=request.source,
                status=(
                    ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
                ),
                submitted=False,
                requires_manual_intervention=True,
                reason=(
                    "No application executor is configured for "
                    "this job source."
                ),
                error_code="executor_not_configured",
                metadata={
                    "source": request.source.value,
                },
            )

        try:
            result = self._executor.execute(request)

        except Exception as exc:
            return ApplicationExecutionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                source=request.source,
                status=ApplicationExecutionStatus.FAILED,
                submitted=False,
                requires_manual_intervention=False,
                reason=(
                    "Application executor failed during execution."
                ),
                error_code="executor_execution_failed",
                metadata={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )

        # Keep identity validation outside the executor exception
        # handler. An identity mismatch must never be silently converted
        # into an ordinary execution failure.
        return self._normalize_result(
            request,
            result,
        )

    @staticmethod
    def _normalize_result(
        request: ApplicationExecutionRequest,
        result: ApplicationExecutionResult,
    ) -> ApplicationExecutionResult:
        """Verify that the executor returned the expected identity."""

        if result.application_id != request.application_id:
            raise ValueError(
                "Executor returned a different application_id."
            )

        if result.external_job_id != request.external_job_id:
            raise ValueError(
                "Executor returned a different external_job_id."
            )

        if result.source != request.source:
            raise ValueError(
                "Executor returned a different source."
            )

        return result

    @staticmethod
    def create_context(
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionContext:
        """Create a READY execution context."""

        return ApplicationExecutionContext(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=ApplicationExecutionStatus.READY,
            metadata=dict(request.metadata),
        )

    @staticmethod
    def start_context(
        context: ApplicationExecutionContext,
    ) -> ApplicationExecutionContext:
        """Move a READY context to STARTED."""

        if (
            context.status
            != ApplicationExecutionStatus.READY
        ):
            raise ValueError(
                "Execution context must be READY before starting."
            )

        return context.start()

    @staticmethod
    def record_form(
        context: ApplicationExecutionContext,
        *,
        fields_detected: int,
    ) -> ApplicationExecutionContext:
        """Record that an application form was detected."""

        if (
            context.status
            not in {
                ApplicationExecutionStatus.STARTED,
                ApplicationExecutionStatus.FORM_DETECTED,
            }
        ):
            raise ValueError(
                "Application form can only be recorded after "
                "execution has started."
            )

        return context.form_detected(
            fields_detected=fields_detected
        )

    @staticmethod
    def record_fields(
        context: ApplicationExecutionContext,
        *,
        fields_filled: int,
    ) -> ApplicationExecutionContext:
        """Record the number of fields that can be filled."""

        if (
            context.status
            not in {
                ApplicationExecutionStatus.FORM_DETECTED,
                ApplicationExecutionStatus.FIELDS_MAPPED,
            }
        ):
            raise ValueError(
                "Fields can only be recorded after a form "
                "has been detected."
            )

        return context.fields_mapped(
            fields_filled=fields_filled
        )


__all__ = [
    "ApplicationExecutorPort",
    "ApplicationExecutorService",
]
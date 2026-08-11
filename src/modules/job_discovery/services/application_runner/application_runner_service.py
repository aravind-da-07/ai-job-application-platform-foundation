"""
Application Runner Service.

Coordinates the lifecycle of a single queued application.

This service is intentionally independent of Playwright or any specific
job portal. Browser execution will be connected later through an
infrastructure adapter.

Lifecycle:

    QUEUED
       ↓
    IN_PROGRESS
       ├── SUBMITTED
       ├── FAILED
       ├── AUTHENTICATION_REQUIRED
       ├── CAPTCHA_DETECTED
       └── MANUAL_REVIEW_REQUIRED
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from src.modules.job_discovery.domain.application_runner import (
    ApplicationRunRequest,
    ApplicationRunResult,
    ApplicationRunState,
    utc_now,
)
from src.shared.config.constants import (
    ApplicationResult,
    ApplicationStatus,
)


class ApplicationRunnerService:
    """
    Manage application execution lifecycle.

    The service does not perform browser automation itself.

    Instead, it maintains a safe state machine that a future portal
    executor can use.
    """

    _TERMINAL_STATUSES = frozenset(
        {
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.FAILED,
            ApplicationStatus.SKIPPED,
            ApplicationStatus.DUPLICATE,
            ApplicationStatus.AUTHENTICATION_REQUIRED,
            ApplicationStatus.CAPTCHA_DETECTED,
            ApplicationStatus.MANUAL_REVIEW_REQUIRED,
        }
    )

    def __init__(self) -> None:
        self._states: dict[
            str,
            ApplicationRunState,
        ] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Return number of tracked application runs."""

        return len(self._states)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        request: ApplicationRunRequest,
    ) -> ApplicationRunState:
        """
        Register a queued application.

        Registration is idempotent for the same application ID.
        """

        existing = self._states.get(
            request.application_id
        )

        if existing is not None:
            return existing

        state = ApplicationRunState(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=ApplicationStatus.QUEUED,
            attempt_number=0,
            maximum_attempts=request.maximum_attempts,
            last_result=ApplicationResult.PENDING,
            metadata=dict(request.metadata),
        )

        self._states[
            request.application_id
        ] = state

        return state

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(
        self,
        application_id: str,
    ) -> ApplicationRunState:
        """Return the current state for an application."""

        state = self._states.get(application_id)

        if state is None:
            raise KeyError(
                f"Application '{application_id}' is not registered."
            )

        return state

    def has(
        self,
        application_id: str,
    ) -> bool:
        """Return whether an application is registered."""

        return application_id in self._states

    def list_states(
        self,
    ) -> list[ApplicationRunState]:
        """Return all tracked application states."""

        return list(self._states.values())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(
        self,
        application_id: str,
    ) -> ApplicationRunState:
        """
        Move a queued application into IN_PROGRESS.

        A terminal application cannot be started again.
        """

        state = self.get(application_id)

        if state.status in self._TERMINAL_STATUSES:
            raise ValueError(
                "Terminal application cannot be started again: "
                f"{state.status.value}"
            )

        if state.status == ApplicationStatus.IN_PROGRESS:
            return state

        if state.status != ApplicationStatus.QUEUED:
            raise ValueError(
                "Application must be queued before it can start."
            )

        if (
            state.attempt_number
            >= state.maximum_attempts
        ):
            raise ValueError(
                "Maximum application attempts reached."
            )

        updated = replace(
            state,
            status=ApplicationStatus.IN_PROGRESS,
            attempt_number=state.attempt_number + 1,
            last_result=ApplicationResult.PENDING,
            started_at=utc_now(),
            completed_at=None,
            reason=None,
            error_code=None,
            requires_manual_intervention=False,
        )

        self._states[
            application_id
        ] = updated

        return updated

    # ------------------------------------------------------------------
    # Completion states
    # ------------------------------------------------------------------

    def mark_submitted(
        self,
        application_id: str,
        *,
        reason: str = "Application submitted successfully.",
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationRunState:
        """
        Mark an application as successfully submitted.
        """

        state = self._require_in_progress(
            application_id
        )

        updated = replace(
            state,
            status=ApplicationStatus.SUBMITTED,
            last_result=ApplicationResult.YES,
            completed_at=utc_now(),
            reason=reason,
            error_code=None,
            requires_manual_intervention=False,
            metadata=self._merge_metadata(
                state.metadata,
                metadata,
            ),
        )

        self._states[
            application_id
        ] = updated

        return updated

    def mark_failed(
        self,
        application_id: str,
        *,
        reason: str,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationRunState:
        """
        Mark an application attempt as failed.

        A failed application can be re-queued for another attempt
        only when the caller explicitly decides to retry it.
        """

        if not reason.strip():
            raise ValueError(
                "Failure reason cannot be empty."
            )

        state = self._require_in_progress(
            application_id
        )

        updated = replace(
            state,
            status=ApplicationStatus.FAILED,
            last_result=ApplicationResult.NO,
            completed_at=utc_now(),
            reason=reason,
            error_code=error_code,
            requires_manual_intervention=False,
            metadata=self._merge_metadata(
                state.metadata,
                metadata,
            ),
        )

        self._states[
            application_id
        ] = updated

        return updated

    # ------------------------------------------------------------------
    # Security / intervention states
    # ------------------------------------------------------------------

    def mark_authentication_required(
        self,
        application_id: str,
        *,
        reason: str = (
            "Authentication is required before the application "
            "can continue."
        ),
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationRunState:
        """
        Mark an application as requiring authentication.

        The runner does not attempt to bypass authentication or MFA.
        """

        state = self._require_in_progress(
            application_id
        )

        updated = replace(
            state,
            status=ApplicationStatus.AUTHENTICATION_REQUIRED,
            last_result=ApplicationResult.PENDING,
            completed_at=utc_now(),
            reason=reason,
            error_code="authentication_required",
            requires_manual_intervention=True,
            metadata=self._merge_metadata(
                state.metadata,
                metadata,
            ),
        )

        self._states[
            application_id
        ] = updated

        return updated

    def mark_captcha_detected(
        self,
        application_id: str,
        *,
        reason: str = (
            "CAPTCHA was detected. Application requires "
            "manual intervention."
        ),
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationRunState:
        """
        Mark an application as blocked by CAPTCHA.

        CAPTCHA is not bypassed by the runner.
        """

        state = self._require_in_progress(
            application_id
        )

        updated = replace(
            state,
            status=ApplicationStatus.CAPTCHA_DETECTED,
            last_result=ApplicationResult.PENDING,
            completed_at=utc_now(),
            reason=reason,
            error_code="captcha_detected",
            requires_manual_intervention=True,
            metadata=self._merge_metadata(
                state.metadata,
                metadata,
            ),
        )

        self._states[
            application_id
        ] = updated

        return updated

    def mark_manual_review_required(
        self,
        application_id: str,
        *,
        reason: str = (
            "Application requires manual review before it "
            "can continue."
        ),
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationRunState:
        """
        Mark an application as requiring manual review.
        """

        state = self._require_in_progress(
            application_id
        )

        updated = replace(
            state,
            status=ApplicationStatus.MANUAL_REVIEW_REQUIRED,
            last_result=ApplicationResult.PENDING,
            completed_at=utc_now(),
            reason=reason,
            error_code="manual_review_required",
            requires_manual_intervention=True,
            metadata=self._merge_metadata(
                state.metadata,
                metadata,
            ),
        )

        self._states[
            application_id
        ] = updated

        return updated

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    def retry(
        self,
        application_id: str,
    ) -> ApplicationRunState:
        """
        Re-queue a failed application when attempts remain.

        Security/intervention states are intentionally not retried
        automatically.
        """

        state = self.get(application_id)

        if state.status != ApplicationStatus.FAILED:
            raise ValueError(
                "Only failed applications can be retried."
            )

        if (
            state.attempt_number
            >= state.maximum_attempts
        ):
            raise ValueError(
                "Maximum application attempts reached."
            )

        updated = replace(
            state,
            status=ApplicationStatus.QUEUED,
            last_result=ApplicationResult.PENDING,
            completed_at=None,
            reason=None,
            error_code=None,
            requires_manual_intervention=False,
        )

        self._states[
            application_id
        ] = updated

        return updated

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_in_progress(
        self,
        application_id: str,
    ) -> ApplicationRunState:
        """
        Return the state only when execution is in progress.
        """

        state = self.get(application_id)

        if state.status != ApplicationStatus.IN_PROGRESS:
            raise ValueError(
                "Application must be IN_PROGRESS for this operation. "
                f"Current status: {state.status.value}"
            )

        return state

    @staticmethod
    def _merge_metadata(
        existing: dict[str, Any],
        additional: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Merge lifecycle metadata without mutating the original state.
        """

        merged = dict(existing)

        if additional:
            merged.update(additional)

        return merged


__all__ = [
    "ApplicationRunnerService",
]
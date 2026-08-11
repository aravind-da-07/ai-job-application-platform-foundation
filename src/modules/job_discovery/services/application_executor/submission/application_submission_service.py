"""
Application submission service.

Coordinates the final submission boundary after application fields
have been successfully verified.

This service does not interact directly with a browser. A submitter
implementation is injected into it.
"""

from __future__ import annotations

from typing import Protocol

from src.modules.job_discovery.domain.application_executor.submission import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionResult,
    ApplicationSubmissionStatus,
)


class ApplicationSubmitter(Protocol):
    """Browser/infrastructure submission contract."""

    async def submit(
        self,
        request: ApplicationSubmissionRequest,
    ) -> ApplicationSubmissionResult:
        """Submit an already verified application."""
        ...


class ApplicationSubmissionService:
    """
    Coordinates the final application submission.

    Submission is allowed only when at least one field has been
    verified successfully.
    """

    def __init__(
        self,
        submitter: ApplicationSubmitter | None = None,
    ) -> None:
        self._submitter = submitter

    @property
    def submitter_configured(self) -> bool:
        """Return whether a submission implementation is configured."""

        return self._submitter is not None

    async def submit(
        self,
        request: ApplicationSubmissionRequest,
    ) -> ApplicationSubmissionResult:
        """
        Submit a verified application.

        This method refuses to submit when no verified fields exist
        or when no submitter has been configured.
        """

        if request.verified_field_count <= 0:
            return ApplicationSubmissionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                status=ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED,
                submitted=False,
                verified_field_count=(
                    request.verified_field_count
                ),
                error_code="no_verified_fields",
                error_message=(
                    "Application cannot be submitted because "
                    "no fields have been successfully verified."
                ),
                manual_intervention_required=True,
            )

        if self._submitter is None:
            return ApplicationSubmissionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                status=ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED,
                submitted=False,
                verified_field_count=(
                    request.verified_field_count
                ),
                error_code="submitter_not_configured",
                error_message=(
                    "No application submitter is configured."
                ),
                manual_intervention_required=True,
            )

        return await self._submitter.submit(request)
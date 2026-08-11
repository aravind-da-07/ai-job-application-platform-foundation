"""
LinkedIn application executor.

This module connects the application-executor contract to the
LinkedIn browser execution workflow.

The synchronous execute() method remains available for the existing
ApplicationExecutorPort contract.

The asynchronous execute_async() method is the preferred path when
using a real Playwright Page because Playwright objects must remain
on their owning event loop.

Authentication, CAPTCHA, manual review, and unsafe application flows
are never bypassed.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionRequest,
    ApplicationExecutionResult,
    ApplicationExecutionStatus,
)
from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormType,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.form_detector import (
    LinkedInApplicationFormDetector,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.mapping.field_mapper import (
    LinkedInApplicationFieldMapper,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.workflow import (
    LinkedInBrowserExecutionWorkflow,
)
from src.modules.job_discovery.services.application_executor import (
    ApplicationExecutorPort,
)
from src.modules.job_discovery.services.application_executor.answers import (
    AnswerResolverService,
)
from src.shared.config.constants import JobSourceType


class LinkedInApplicationExecutor(ApplicationExecutorPort):
    """
    LinkedIn-specific application executor.

    execute()
        Synchronous compatibility boundary.

    execute_async()
        Preferred browser/Playwright execution path.
    """

    source = JobSourceType.LINKEDIN

    def __init__(
        self,
        browser_session: Any | None = None,
        answer_resolver: AnswerResolverService | None = None,
        browser_workflow: LinkedInBrowserExecutionWorkflow | None = None,
    ) -> None:
        self._browser_session = browser_session

        self._answer_resolver = (
            answer_resolver
            if answer_resolver is not None
            else AnswerResolverService()
        )

        self._browser_workflow = (
            browser_workflow
            if browser_workflow is not None
            else LinkedInBrowserExecutionWorkflow()
        )

    @property
    def configured(self) -> bool:
        """Return whether a browser session is configured."""

        return self._browser_session is not None

    async def execute_async(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:
        """
        Execute a LinkedIn application asynchronously.

        This is the preferred method for real Playwright execution.
        """

        self._validate_request(request)

        if request.source != self.source:
            raise ValueError(
                "LinkedIn executor received a non-LinkedIn job."
            )

        if self._browser_session is None:
            return self._browser_not_configured_result(
                request
            )

        try:
            return await self._execute_browser_workflow(
                request
            )

        except Exception as exc:
            return ApplicationExecutionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                source=request.source,
                status=ApplicationExecutionStatus.FAILED,
                submitted=False,
                requires_manual_intervention=True,
                reason=(
                    "LinkedIn browser execution failed "
                    "unexpectedly."
                ),
                error_code="linkedin_executor_failed",
                metadata={
                    "portal": "linkedin",
                    "exception": str(exc),
                },
            )

    def execute(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:
        """
        Execute a LinkedIn application synchronously.

        This preserves the existing ApplicationExecutorPort contract.

        Real Playwright callers running inside an event loop should use
        execute_async() instead.
        """

        self._validate_request(request)

        if request.source != self.source:
            raise ValueError(
                "LinkedIn executor received a non-LinkedIn job."
            )

        if self._browser_session is None:
            return self._browser_not_configured_result(
                request
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.execute_async(request)
            )

        raise RuntimeError(
            "LinkedInApplicationExecutor.execute() cannot be "
            "called from an active asyncio event loop. "
            "Use execute_async() for Playwright execution."
        )

    async def _execute_browser_workflow(
        self,
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:
        """
        Detect the LinkedIn application form, resolve candidate
        answers, and delegate execution to the browser workflow.
        """

        # ----------------------------------------------------------
        # 1. Detect current application form
        # ----------------------------------------------------------

        detector = LinkedInApplicationFormDetector(
            self._browser_session
        )

        snapshot = await detector.detect_async()

        form_type = snapshot.form_type

        # ----------------------------------------------------------
        # 2. Safety gates
        #
        # These flows must never receive automatic answers.
        # ----------------------------------------------------------

        if form_type == ApplicationFormType.AUTHENTICATION_REQUIRED:
            return self._manual_review_result(
                request=request,
                reason=(
                    "LinkedIn authentication is required "
                    "before the application can continue."
                ),
                error_code="authentication_required",
                metadata={
                    "form_type": form_type.value,
                },
            )

        if form_type == ApplicationFormType.CAPTCHA_DETECTED:
            return self._manual_review_result(
                request=request,
                reason=(
                    "CAPTCHA detected. Manual intervention "
                    "is required."
                ),
                error_code="captcha_detected",
                metadata={
                    "form_type": form_type.value,
                },
            )

        if form_type == ApplicationFormType.EXTERNAL_APPLICATION:
            return self._manual_review_result(
                request=request,
                reason=(
                    "Application redirects to an external "
                    "application flow."
                ),
                error_code="external_application",
                metadata={
                    "form_type": form_type.value,
                },
            )

        if form_type != ApplicationFormType.EASY_APPLY:
            return self._manual_review_result(
                request=request,
                reason=(
                    "LinkedIn application flow could not "
                    "be safely recognized."
                ),
                error_code="unknown_application_flow",
                metadata={
                    "form_type": form_type.value,
                },
            )

        # ----------------------------------------------------------
        # 3. Map detected fields
        # ----------------------------------------------------------

        mapper = LinkedInApplicationFieldMapper()

        mapped_fields = mapper.map_fields(
            tuple(snapshot.fields)
        )

        # ----------------------------------------------------------
        # 4. Resolve candidate-provided answers
        # ----------------------------------------------------------

        resolution = self._answer_resolver.resolve_fields(
            mapped_fields,
            request.candidate_data,
        )

        # ----------------------------------------------------------
        # 5. Delegate browser execution
        # ----------------------------------------------------------

        workflow_result = (
            await self._browser_workflow.execute(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                page=self._browser_session,
                resolution=resolution,
            )
        )

        # ----------------------------------------------------------
        # 6. Convert workflow result to executor result
        # ----------------------------------------------------------

        return self._to_execution_result(
            request=request,
            workflow_result=workflow_result,
        )

    @staticmethod
    def _to_execution_result(
        *,
        request: ApplicationExecutionRequest,
        workflow_result: Any,
    ) -> ApplicationExecutionResult:
        """
        Convert LinkedInBrowserExecutionResult into the normalized
        ApplicationExecutionResult domain model.
        """

        submission = workflow_result.submission

        # ----------------------------------------------------------
        # Final success boundary
        # ----------------------------------------------------------

        if (
            workflow_result.completed
            and submission is not None
            and submission.submitted
            and submission.confirmation_id
        ):
            return ApplicationExecutionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                source=request.source,
                status=ApplicationExecutionStatus.SUBMITTED,
                submitted=True,
                requires_manual_intervention=False,
                reason=(
                    workflow_result.reason
                    or (
                        "LinkedIn application was successfully "
                        "submitted and confirmed."
                    )
                ),
                fields_detected=(
                    workflow_result.fields_detected
                ),
                fields_filled=(
                    workflow_result.fields_filled
                ),
                metadata={
                    "portal": "linkedin",
                    "form_type": (
                        workflow_result.form_type.value
                    ),
                    "workflow_completed": True,
                    "confirmation_id": (
                        submission.confirmation_id
                    ),
                    "submission_status": (
                        submission.status.value
                    ),
                },
            )

        # ----------------------------------------------------------
        # Manual intervention boundary
        # ----------------------------------------------------------

        if workflow_result.requires_manual_intervention:
            return ApplicationExecutionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                source=request.source,
                status=(
                    ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
                ),
                submitted=False,
                requires_manual_intervention=True,
                reason=workflow_result.reason,
                error_code=workflow_result.error_code,
                fields_detected=(
                    workflow_result.fields_detected
                ),
                fields_filled=(
                    workflow_result.fields_filled
                ),
                metadata={
                    "portal": "linkedin",
                    "form_type": (
                        workflow_result.form_type.value
                    ),
                    "workflow_completed": False,
                },
            )

        # ----------------------------------------------------------
        # Failed execution/submission boundary
        # ----------------------------------------------------------

        return ApplicationExecutionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=ApplicationExecutionStatus.FAILED,
            submitted=False,
            requires_manual_intervention=True,
            reason=workflow_result.reason,
            error_code=workflow_result.error_code,
            fields_detected=(
                workflow_result.fields_detected
            ),
            fields_filled=(
                workflow_result.fields_filled
            ),
            metadata={
                "portal": "linkedin",
                "form_type": (
                    workflow_result.form_type.value
                ),
                "workflow_completed": False,
            },
        )

    @staticmethod
    def _browser_not_configured_result(
        request: ApplicationExecutionRequest,
    ) -> ApplicationExecutionResult:
        """Return a safe result when no browser session exists."""

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
                "LinkedIn browser session is not configured."
            ),
            error_code="linkedin_browser_not_configured",
            metadata={
                "portal": "linkedin",
                "executor_configured": False,
            },
        )

    @staticmethod
    def _manual_review_result(
        *,
        request: ApplicationExecutionRequest,
        reason: str,
        error_code: str,
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationExecutionResult:
        """Create a safe manual-review result."""

        result_metadata = {
            "portal": "linkedin",
        }

        if metadata:
            result_metadata.update(metadata)

        return ApplicationExecutionResult(
            application_id=request.application_id,
            external_job_id=request.external_job_id,
            source=request.source,
            status=(
                ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
            ),
            submitted=False,
            requires_manual_intervention=True,
            reason=reason,
            error_code=error_code,
            metadata=result_metadata,
        )

    @staticmethod
    def _validate_request(
        request: ApplicationExecutionRequest,
    ) -> None:
        """Validate that the request contains usable LinkedIn data."""

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
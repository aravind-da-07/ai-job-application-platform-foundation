"""
Playwright-backed LinkedIn application submitter.

This component performs the final browser submission only after the
application execution layer has verified the required fields.

It does not bypass authentication or CAPTCHA.
"""

from __future__ import annotations

import uuid

from playwright.async_api import Page

from src.modules.job_discovery.domain.application_executor.submission import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionResult,
    ApplicationSubmissionStatus,
)


class PlaywrightLinkedInApplicationSubmitter:
    """
    Browser-backed application submitter.

    The submit button and confirmation marker are deliberately
    configurable so the implementation can later be adapted to
    portal-specific DOM structures.
    """

    def __init__(
        self,
        page: Page,
        submit_selector: str = '[data-submit-button="true"]',
        confirmation_selector: str = '[data-submission-confirmation="true"]',
    ) -> None:
        self.page = page
        self.submit_selector = submit_selector
        self.confirmation_selector = confirmation_selector

    async def submit(
        self,
        request: ApplicationSubmissionRequest,
    ) -> ApplicationSubmissionResult:
        """
        Submit an already verified application.

        A successful result is returned only when the confirmation
        marker is observed after the submit action.
        """

        try:
            submit_button = self.page.locator(
                self.submit_selector
            ).first

            if await submit_button.count() == 0:
                return ApplicationSubmissionResult(
                    application_id=request.application_id,
                    external_job_id=request.external_job_id,
                    status=ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED,
                    submitted=False,
                    verified_field_count=(
                        request.verified_field_count
                    ),
                    error_code="submit_button_not_found",
                    error_message=(
                        "Application submit button could not "
                        "be located."
                    ),
                    manual_intervention_required=True,
                )

            if not await submit_button.is_visible():
                return ApplicationSubmissionResult(
                    application_id=request.application_id,
                    external_job_id=request.external_job_id,
                    status=ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED,
                    submitted=False,
                    verified_field_count=(
                        request.verified_field_count
                    ),
                    error_code="submit_button_not_visible",
                    error_message=(
                        "Application submit button is not visible."
                    ),
                    manual_intervention_required=True,
                )

            if not await submit_button.is_enabled():
                return ApplicationSubmissionResult(
                    application_id=request.application_id,
                    external_job_id=request.external_job_id,
                    status=ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED,
                    submitted=False,
                    verified_field_count=(
                        request.verified_field_count
                    ),
                    error_code="submit_button_disabled",
                    error_message=(
                        "Application submit button is disabled."
                    ),
                    manual_intervention_required=True,
                )

            await submit_button.click()

            confirmation = self.page.locator(
                self.confirmation_selector
            ).first

            try:
                await confirmation.wait_for(
                    state="visible",
                    timeout=5000,
                )
            except Exception:
                return ApplicationSubmissionResult(
                    application_id=request.application_id,
                    external_job_id=request.external_job_id,
                    status=ApplicationSubmissionStatus.FAILED,
                    submitted=False,
                    verified_field_count=(
                        request.verified_field_count
                    ),
                    error_code="submission_confirmation_not_detected",
                    error_message=(
                        "Submit action completed, but the expected "
                        "submission confirmation was not detected."
                    ),
                )

            confirmation_id = (
                await confirmation.get_attribute(
                    "data-confirmation-id"
                )
            )

            if not confirmation_id:
                confirmation_id = (
                    await confirmation.get_attribute(
                        "data-submission-id"
                    )
                )

            if not confirmation_id:
                return ApplicationSubmissionResult(
                    application_id=request.application_id,
                    external_job_id=request.external_job_id,
                    status=ApplicationSubmissionStatus.FAILED,
                    submitted=False,
                    verified_field_count=(
                        request.verified_field_count
                    ),
                    error_code="confirmation_id_missing",
                    error_message=(
                        "Submission confirmation was detected, "
                        "but no confirmation ID was provided."
                    ),
                )

            return ApplicationSubmissionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                status=ApplicationSubmissionStatus.SUBMITTED,
                submitted=True,
                verified_field_count=(
                    request.verified_field_count
                ),
                confirmation_id=confirmation_id,
                metadata={
                    "confirmation_detected": True,
                },
            )

        except Exception as exc:
            return ApplicationSubmissionResult(
                application_id=request.application_id,
                external_job_id=request.external_job_id,
                status=ApplicationSubmissionStatus.FAILED,
                submitted=False,
                verified_field_count=(
                    request.verified_field_count
                ),
                error_code="browser_submission_failed",
                error_message=str(exc),
            )
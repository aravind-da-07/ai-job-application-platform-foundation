"""
Playwright-backed LinkedIn application field filler.

This component fills only answers that have already been approved as
AUTO_ANSWER by the application planning layer.

It does not bypass authentication, CAPTCHA, or manual-review states.
"""

from __future__ import annotations

from typing import Any

from playwright.async_api import Locator, Page

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
    ApplicationAnswerDecision,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling.field_filler import (
    FieldFillResult,
)


class PlaywrightLinkedInApplicationFieldFiller:
    """
    Browser-backed application field filler.

    The implementation intentionally uses conservative selectors and
    verifies the resulting field value after filling.
    """

    def __init__(
        self,
        page: Page,
    ) -> None:
        self.page = page

    async def fill_field(
        self,
        answer: ApplicationAnswer,
    ) -> FieldFillResult:
        """
        Fill one approved application answer.

        Only AUTO_ANSWER values are accepted.
        """

        if (
            answer.decision
            != ApplicationAnswerDecision.AUTO_ANSWER
        ):
            return FieldFillResult(
                field_id=answer.field_id,
                success=False,
                error_code="answer_not_approved",
                error_message=(
                    "Only AUTO_ANSWER fields may be filled."
                ),
            )

        if answer.value is None or not answer.value.strip():
            return FieldFillResult(
                field_id=answer.field_id,
                success=False,
                error_code="empty_answer",
                error_message=(
                    "Approved answer contains no value."
                ),
            )

        try:
            locator = await self._locate_field(
                answer.field_id
            )

            if locator is None:
                return FieldFillResult(
                    field_id=answer.field_id,
                    success=False,
                    error_code="field_not_found",
                    error_message=(
                        "Application field could not be located."
                    ),
                )

            tag_name = await locator.evaluate(
                "(element) => element.tagName.toLowerCase()"
            )

            input_type = await locator.get_attribute("type")

            if tag_name == "select":
                await locator.select_option(
                    label=answer.value
                )

            elif input_type in {
                "checkbox",
                "radio",
            }:
                await locator.check()

            else:
                await locator.fill(answer.value)

            verified = await self._verify_value(
                locator,
                answer.value,
                tag_name,
                input_type,
            )

            if not verified:
                return FieldFillResult(
                    field_id=answer.field_id,
                    success=False,
                    error_code="verification_failed",
                    error_message=(
                        "Field was interacted with but the "
                        "expected value could not be verified."
                    ),
                )

            return FieldFillResult(
                field_id=answer.field_id,
                success=True,
                filled_value=answer.value,
                metadata={
                    "normalized_field_name": (
                        answer.normalized_field_name
                    ),
                    "tag_name": tag_name,
                    "input_type": input_type,
                },
            )

        except Exception as exc:
            return FieldFillResult(
                field_id=answer.field_id,
                success=False,
                error_code="browser_fill_failed",
                error_message=str(exc),
            )

    async def _locate_field(
        self,
        field_id: str,
    ) -> Locator | None:
        """
        Locate a form field using its stable field identifier.

        The test form and future adapter should expose a stable
        data-field-id attribute where possible.
        """

        locator = self.page.locator(
            f'[data-field-id="{field_id}"]'
        ).first

        if await locator.count() > 0:
            return locator

        locator = self.page.locator(
            f'#{field_id}'
        ).first

        if await locator.count() > 0:
            return locator

        return None

    async def _verify_value(
        self,
        locator: Locator,
        expected_value: str,
        tag_name: str,
        input_type: str | None,
    ) -> bool:
        """
        Verify that the browser contains the expected value.
        """

        if input_type == "checkbox":
            return await locator.is_checked()

        if input_type == "radio":
            return await locator.is_checked()

        if tag_name == "select":
            selected_value = await locator.input_value()

            selected_label = await locator.locator(
                "option:checked"
            ).text_content()

            return (
                selected_value == expected_value
                or (
                    selected_label is not None
                    and selected_label.strip()
                    == expected_value.strip()
                )
            )

        actual_value = await locator.input_value()

        return actual_value == expected_value
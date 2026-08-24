"""
Playwright-backed LinkedIn application field filler.

This component fills only answers that have already been approved as
AUTO_ANSWER by the application planning layer.

It does not bypass authentication, CAPTCHA, OTP, or manual-review states.

Supported interactions include:

- text inputs
- textareas
- contenteditable fields
- select/dropdown fields
- checkbox fields
- radio fields
- file uploads
- stable data-field-id selectors
- id/name/label/aria-label fallbacks
- post-fill verification
- limited retry for transient browser failures
"""

from __future__ import annotations

import re
from typing import Any

from playwright.async_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

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

    Only AUTO_ANSWER values are accepted.

    The implementation uses progressively broader selectors and
    verifies the resulting browser state after filling.
    """

    _MAX_ATTEMPTS = 2

    _TEXT_INPUT_TYPES = {
        None,
        "",
        "text",
        "email",
        "tel",
        "number",
        "url",
        "search",
        "date",
        "datetime-local",
        "month",
        "week",
        "time",
    }

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

        if (
            answer.value is None
            or not answer.value.strip()
        ):
            return FieldFillResult(
                field_id=answer.field_id,
                success=False,
                error_code="empty_answer",
                error_message=(
                    "Approved answer contains no value."
                ),
            )

        # ----------------------------------------------------------
        # Attempt ordinary browser interaction more than once.
        # ----------------------------------------------------------

        last_error: Exception | None = None

        for attempt in range(
            1,
            self._MAX_ATTEMPTS + 1,
        ):
            try:
                locator = await self._locate_field(
                    answer
                )

                if locator is None:
                    return FieldFillResult(
                        field_id=answer.field_id,
                        success=False,
                        error_code="field_not_found",
                        error_message=(
                            "Application field could not be "
                            "located using supported selectors."
                        ),
                        metadata={
                            "attempt": attempt,
                        },
                    )

                field_info = (
                    await self._inspect_field(
                        locator
                    )
                )

                await self._fill_by_field_type(
                    locator=locator,
                    answer=answer,
                    field_info=field_info,
                )

                verified = (
                    await self._verify_value(
                        locator=locator,
                        expected_value=answer.value,
                        field_info=field_info,
                    )
                )

                if not verified:
                    if attempt < self._MAX_ATTEMPTS:
                        continue

                    return FieldFillResult(
                        field_id=answer.field_id,
                        success=False,
                        error_code="verification_failed",
                        error_message=(
                            "Field was interacted with but "
                            "the expected value could not "
                            "be verified."
                        ),
                        metadata={
                            **field_info,
                            "attempt": attempt,
                        },
                    )

                return FieldFillResult(
                    field_id=answer.field_id,
                    success=True,
                    filled_value=answer.value,
                    metadata={
                        **field_info,
                        "attempt": attempt,
                        "normalized_field_name": (
                            answer.normalized_field_name
                        ),
                    },
                )

            except PlaywrightTimeoutError as exc:
                last_error = exc

                if attempt < self._MAX_ATTEMPTS:
                    continue

            except Exception as exc:
                last_error = exc

                if attempt < self._MAX_ATTEMPTS:
                    continue

        return FieldFillResult(
            field_id=answer.field_id,
            success=False,
            error_code="browser_fill_failed",
            error_message=(
                str(last_error)
                if last_error is not None
                else "Unknown browser fill failure."
            ),
            metadata={
                "attempts": self._MAX_ATTEMPTS,
            },
        )

    # ==============================================================
    # Field discovery
    # ==============================================================

    async def _locate_field(
        self,
        answer: ApplicationAnswer,
    ) -> Locator | None:
        """
        Locate an application field.

        Selector priority:

        1. data-field-id
        2. exact id
        3. exact name
        4. aria-label
        5. associated label
        6. field metadata selectors
        """

        field_id = answer.field_id.strip()

        # ----------------------------------------------------------
        # 1. Stable data-field-id
        # ----------------------------------------------------------

        locator = self.page.locator(
            f'[data-field-id="{self._css_escape(field_id)}"]'
        ).first

        if await locator.count() > 0:
            return locator

        # ----------------------------------------------------------
        # 2. Exact id
        # ----------------------------------------------------------

        locator = self.page.locator(
            f'#{self._css_escape(field_id)}'
        ).first

        if await locator.count() > 0:
            return locator

        # ----------------------------------------------------------
        # Metadata-provided selectors
        # ----------------------------------------------------------

        metadata = answer.metadata or {}

        for key in (
            "selector",
            "css_selector",
            "dom_selector",
        ):
            selector = metadata.get(key)

            if not selector:
                continue

            try:
                locator = self.page.locator(
                    str(selector)
                ).first

                if await locator.count() > 0:
                    return locator
            except Exception:
                continue

        # ----------------------------------------------------------
        # Name
        # ----------------------------------------------------------

        name = metadata.get("name")

        if name:
            locator = self.page.locator(
                f'[name="{self._css_escape(str(name))}"]'
            ).first

            if await locator.count() > 0:
                return locator

        # ----------------------------------------------------------
        # Aria label
        # ----------------------------------------------------------

        aria_label = metadata.get(
            "aria_label"
        )

        if aria_label:
            locator = self.page.get_by_label(
                str(aria_label),
                exact=False,
            ).first

            if await locator.count() > 0:
                return locator

        # ----------------------------------------------------------
        # Original application label
        # ----------------------------------------------------------

        original_label = metadata.get(
            "original_label"
        )

        if original_label:
            try:
                locator = self.page.get_by_label(
                    str(original_label),
                    exact=False,
                ).first

                if await locator.count() > 0:
                    return locator
            except Exception:
                pass

        # ----------------------------------------------------------
        # Stable normalized field name
        # ----------------------------------------------------------

        normalized_name = (
            answer.normalized_field_name
        )

        if normalized_name:
            candidates = (
                normalized_name,
                normalized_name.replace(
                    "_",
                    " ",
                ),
            )

            for candidate in candidates:
                try:
                    locator = self.page.get_by_label(
                        candidate,
                        exact=False,
                    ).first

                    if await locator.count() > 0:
                        return locator
                except Exception:
                    continue

        return None

    # ==============================================================
    # Field inspection
    # ==============================================================

    async def _inspect_field(
        self,
        locator: Locator,
    ) -> dict[str, Any]:
        """
        Inspect the DOM element before interaction.
        """

        tag_name = (
            await locator.evaluate(
                "(element) => element.tagName.toLowerCase()"
            )
        )

        input_type = await locator.get_attribute(
            "type"
        )

        name = await locator.get_attribute(
            "name"
        )

        element_id = await locator.get_attribute(
            "id"
        )

        aria_label = await locator.get_attribute(
            "aria-label"
        )

        role = await locator.get_attribute(
            "role"
        )

        contenteditable = (
            await locator.get_attribute(
                "contenteditable"
            )
        )

        return {
            "tag_name": tag_name,
            "input_type": input_type,
            "name": name,
            "element_id": element_id,
            "aria_label": aria_label,
            "role": role,
            "contenteditable": contenteditable,
        }

    # ==============================================================
    # Field interaction
    # ==============================================================

    async def _fill_by_field_type(
        self,
        *,
        locator: Locator,
        answer: ApplicationAnswer,
        field_info: dict[str, Any],
    ) -> None:
        """
        Fill a field according to its DOM representation.
        """

        tag_name = field_info.get(
            "tag_name"
        )

        input_type = field_info.get(
            "input_type"
        )

        contenteditable = field_info.get(
            "contenteditable"
        )

        value = answer.value

        if value is None:
            raise ValueError(
                "Cannot fill a field with None."
            )

        # ----------------------------------------------------------
        # File upload
        # ----------------------------------------------------------

        if input_type == "file":
            await self._fill_file(
                locator=locator,
                answer=answer,
            )
            return

        # ----------------------------------------------------------
        # Select
        # ----------------------------------------------------------

        if tag_name == "select":
            await self._fill_select(
                locator=locator,
                value=value,
            )
            return

        # ----------------------------------------------------------
        # Checkbox
        # ----------------------------------------------------------

        if input_type == "checkbox":
            await self._fill_checkbox(
                locator=locator,
                value=value,
            )
            return

        # ----------------------------------------------------------
        # Radio
        # ----------------------------------------------------------

        if input_type == "radio":
            await self._fill_radio(
                locator=locator,
                value=value,
            )
            return

        # ----------------------------------------------------------
        # Contenteditable
        # ----------------------------------------------------------

        if contenteditable == "true":
            await locator.click()
            await locator.fill(value)
            return

        # ----------------------------------------------------------
        # Generic text field
        # ----------------------------------------------------------

        if (
            input_type in self._TEXT_INPUT_TYPES
            or tag_name == "textarea"
        ):
            await locator.fill(value)
            return

        # ----------------------------------------------------------
        # Fallback
        # ----------------------------------------------------------

        await locator.fill(value)

    # ==============================================================
    # Select
    # ==============================================================

    async def _fill_select(
        self,
        *,
        locator: Locator,
        value: str,
    ) -> None:
        """
        Select an option by label first, then value.
        """

        try:
            await locator.select_option(
                label=value
            )
            return
        except Exception:
            pass

        try:
            await locator.select_option(
                value=value
            )
            return
        except Exception:
            pass

        # ----------------------------------------------------------
        # Case-insensitive option-label fallback
        # ----------------------------------------------------------

        options = locator.locator(
            "option"
        )

        option_count = await options.count()

        normalized_expected = (
            self._normalize_text(value)
        )

        for index in range(
            option_count
        ):
            option = options.nth(index)

            label = await option.text_content()

            if label is None:
                continue

            if (
                self._normalize_text(label)
                == normalized_expected
            ):
                option_value = (
                    await option.get_attribute(
                        "value"
                    )
                )

                if option_value is not None:
                    await locator.select_option(
                        value=option_value
                    )
                    return

        raise ValueError(
            f"Could not select option '{value}'."
        )

    # ==============================================================
    # Checkbox
    # ==============================================================

    async def _fill_checkbox(
        self,
        *,
        locator: Locator,
        value: str,
    ) -> None:
        """
        Set checkbox state based on a Yes/No-style answer.
        """

        normalized = self._normalize_text(
            value
        )

        truthy_values = {
            "yes",
            "true",
            "1",
            "checked",
            "on",
        }

        falsy_values = {
            "no",
            "false",
            "0",
            "unchecked",
            "off",
        }

        if normalized in truthy_values:
            if not await locator.is_checked():
                await locator.check()
            return

        if normalized in falsy_values:
            if await locator.is_checked():
                await locator.uncheck()
            return

        raise ValueError(
            f"Unsupported checkbox value: '{value}'."
        )

    # ==============================================================
    # Radio
    # ==============================================================

    async def _fill_radio(
        self,
        *,
        locator: Locator,
        value: str,
    ) -> None:
        """
        Select a radio option.

        If the supplied locator represents a single radio control,
        it is checked directly.

        For grouped radio controls, the metadata may provide a
        group selector.
        """

        metadata = {}

        # The ApplicationAnswer metadata may contain group
        # information. The caller already supplied the individual
        # field locator, so direct selection is the safest default.
        #
        # We intentionally do not guess between unrelated radio
        # controls.

        _ = metadata

        if not await locator.is_checked():
            await locator.check()

    # ==============================================================
    # File upload
    # ==============================================================

    async def _fill_file(
        self,
        *,
        locator: Locator,
        answer: ApplicationAnswer,
    ) -> None:
        """
        Upload a candidate document.

        The answer value must be a valid local file path.
        """

        file_path = (
            answer.value.strip()
        )

        if not file_path:
            raise ValueError(
                "File upload path cannot be empty."
            )

        await locator.set_input_files(
            file_path
        )

    # ==============================================================
    # Verification
    # ==============================================================

    async def _verify_value(
        self,
        *,
        locator: Locator,
        expected_value: str,
        field_info: dict[str, Any],
    ) -> bool:
        """
        Verify that the browser contains the expected value.
        """

        tag_name = field_info.get(
            "tag_name"
        )

        input_type = field_info.get(
            "input_type"
        )

        # ----------------------------------------------------------
        # Checkbox
        # ----------------------------------------------------------

        if input_type == "checkbox":
            normalized = self._normalize_text(
                expected_value
            )

            should_be_checked = normalized in {
                "yes",
                "true",
                "1",
                "checked",
                "on",
            }

            return (
                await locator.is_checked()
            ) == should_be_checked

        # ----------------------------------------------------------
        # Radio
        # ----------------------------------------------------------

        if input_type == "radio":
            return await locator.is_checked()

        # ----------------------------------------------------------
        # File
        # ----------------------------------------------------------

        if input_type == "file":
            return True

        # ----------------------------------------------------------
        # Select
        # ----------------------------------------------------------

        if tag_name == "select":
            selected_value = (
                await locator.input_value()
            )

            selected_label = (
                await locator.locator(
                    "option:checked"
                ).text_content()
            )

            normalized_expected = (
                self._normalize_text(
                    expected_value
                )
            )

            if selected_value == expected_value:
                return True

            if (
                selected_label is not None
                and self._normalize_text(
                    selected_label
                )
                == normalized_expected
            ):
                return True

            return False

        # ----------------------------------------------------------
        # Contenteditable
        # ----------------------------------------------------------

        if (
            field_info.get(
                "contenteditable"
            )
            == "true"
        ):
            actual_text = (
                await locator.text_content()
                or ""
            )

            return (
                self._normalize_text(
                    actual_text
                )
                == self._normalize_text(
                    expected_value
                )
            )

        # ----------------------------------------------------------
        # Normal input / textarea
        # ----------------------------------------------------------

        actual_value = (
            await locator.input_value()
        )

        return (
            actual_value
            == expected_value
        )

    # ==============================================================
    # Utilities
    # ==============================================================

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        """
        Normalize text for case-insensitive comparisons.
        """

        value = value.lower().strip()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value

    @staticmethod
    def _css_escape(
        value: str,
    ) -> str:
        """
        Basic CSS-string escaping for IDs and attributes.
        """

        return (
            value
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )


__all__ = [
    "PlaywrightLinkedInApplicationFieldFiller",
]
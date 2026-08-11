"""
LinkedIn application form detector.

This module inspects an already-loaded LinkedIn page and converts
portal-specific DOM information into the normalized application-form
domain model.

It does not submit applications and does not bypass authentication,
MFA, or CAPTCHA.

The detector supports both:
    - synchronous detection for existing tests/fake pages
    - asynchronous detection for real Playwright async pages
"""

from __future__ import annotations

import inspect
from typing import Any

from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormField,
    ApplicationFormSnapshot,
    ApplicationFormType,
)


class LinkedInApplicationFormDetector:
    """
    Detect LinkedIn application flows.

    `detect()` preserves the original synchronous contract.

    `detect_async()` is used with Playwright's async API.
    """

    def __init__(self, page: Any) -> None:
        self._page = page

    # ==============================================================
    # PUBLIC API
    # ==============================================================

    def detect(self) -> ApplicationFormSnapshot:
        """
        Synchronous detection.

        Preserves compatibility with existing detector tests and
        synchronous fake-page implementations.
        """

        url = self._safe_url_sync()

        if self._authentication_required_sync():
            return ApplicationFormSnapshot(
                form_type=(
                    ApplicationFormType.AUTHENTICATION_REQUIRED
                ),
                url=url,
                detected=False,
                requires_authentication=True,
                metadata={
                    "portal": "linkedin",
                },
            )

        if self._captcha_detected_sync():
            return ApplicationFormSnapshot(
                form_type=ApplicationFormType.CAPTCHA_DETECTED,
                url=url,
                detected=False,
                captcha_detected=True,
                metadata={
                    "portal": "linkedin",
                },
            )

        if self._easy_apply_detected_sync():
            fields = self._extract_fields_sync()

            return ApplicationFormSnapshot(
                form_type=ApplicationFormType.EASY_APPLY,
                url=url,
                fields=tuple(fields),
                detected=True,
                title=self._safe_title_sync(),
                company_name=self._company_name_sync(),
                metadata={
                    "portal": "linkedin",
                    "field_count": len(fields),
                },
            )

        if self._external_application_detected_sync():
            return ApplicationFormSnapshot(
                form_type=(
                    ApplicationFormType.EXTERNAL_APPLICATION
                ),
                url=url,
                detected=True,
                title=self._safe_title_sync(),
                company_name=self._company_name_sync(),
                metadata={
                    "portal": "linkedin",
                },
            )

        return ApplicationFormSnapshot(
            form_type=(
                ApplicationFormType.MANUAL_REVIEW_REQUIRED
            ),
            url=url,
            detected=False,
            metadata={
                "portal": "linkedin",
                "reason": "unrecognized_application_flow",
            },
        )

    async def detect_async(
        self,
    ) -> ApplicationFormSnapshot:
        """
        Asynchronous detection for Playwright's async API.
        """

        url = self._safe_url_sync()

        if await self._authentication_required_async():
            return ApplicationFormSnapshot(
                form_type=(
                    ApplicationFormType.AUTHENTICATION_REQUIRED
                ),
                url=url,
                detected=False,
                requires_authentication=True,
                metadata={
                    "portal": "linkedin",
                },
            )

        if await self._captcha_detected_async():
            return ApplicationFormSnapshot(
                form_type=ApplicationFormType.CAPTCHA_DETECTED,
                url=url,
                detected=False,
                captcha_detected=True,
                metadata={
                    "portal": "linkedin",
                },
            )

        if await self._easy_apply_detected_async():
            fields = await self._extract_fields_async()

            return ApplicationFormSnapshot(
                form_type=ApplicationFormType.EASY_APPLY,
                url=url,
                fields=tuple(fields),
                detected=True,
                title=await self._safe_title_async(),
                company_name=await self._company_name_async(),
                metadata={
                    "portal": "linkedin",
                    "field_count": len(fields),
                },
            )

        if await self._external_application_detected_async():
            return ApplicationFormSnapshot(
                form_type=(
                    ApplicationFormType.EXTERNAL_APPLICATION
                ),
                url=url,
                detected=True,
                title=await self._safe_title_async(),
                company_name=await self._company_name_async(),
                metadata={
                    "portal": "linkedin",
                },
            )

        return ApplicationFormSnapshot(
            form_type=(
                ApplicationFormType.MANUAL_REVIEW_REQUIRED
            ),
            url=url,
            detected=False,
            metadata={
                "portal": "linkedin",
                "reason": "unrecognized_application_flow",
            },
        )

    # ==============================================================
    # SYNCHRONOUS IMPLEMENTATION
    # ==============================================================

    def _safe_url_sync(self) -> str:
        try:
            value = self._page.url

            if inspect.isawaitable(value):
                return ""

            return str(value or "")

        except Exception:
            return ""

    def _safe_title_sync(self) -> str | None:
        try:
            value = self._page.title

            if callable(value):
                value = value()

            if inspect.isawaitable(value):
                return None

            value = str(value or "").strip()

            return value or None

        except Exception:
            return None

    def _authentication_required_sync(self) -> bool:
        selectors = (
            "input[name='session_key']",
            "input[name='session_password']",
            "form[action*='login']",
            "[data-testid='sign-in-form']",
            "[data-login-required='true']",
        )

        return self._any_selector_visible_sync(
            selectors
        )

    def _captcha_detected_sync(self) -> bool:
        selectors = (
            "iframe[src*='captcha']",
            "[id*='captcha']",
            "[class*='captcha']",
            "[data-testid*='captcha']",
            "[data-captcha='true']",
        )

        return self._any_selector_visible_sync(
            selectors
        )

    def _easy_apply_detected_sync(self) -> bool:
        selectors = (
            "button.jobs-apply-button",
            "button[aria-label*='Easy Apply']",
            "button:has-text('Easy Apply')",
            "[data-easy-apply='true']",
        )

        return self._any_selector_visible_sync(
            selectors
        )

    def _external_application_detected_sync(self) -> bool:
        selectors = (
            "a[href*='apply']",
            "button:has-text('Apply')",
            "[data-external-application='true']",
        )

        return self._any_selector_visible_sync(
            selectors
        )

    def _any_selector_visible_sync(
        self,
        selectors: tuple[str, ...],
    ) -> bool:
        for selector in selectors:
            try:
                locator = self._page.locator(selector)
                count = locator.count()

                if inspect.isawaitable(count):
                    continue

                for index in range(count):
                    element = locator.nth(index)
                    visible = element.is_visible()

                    if inspect.isawaitable(visible):
                        continue

                    if visible:
                        return True

            except Exception:
                continue

        return False

    def _extract_fields_sync(
        self,
    ) -> list[ApplicationFormField]:

        fields: list[ApplicationFormField] = []

        selectors = (
            "input",
            "textarea",
            "select",
        )

        field_index = 0

        for selector in selectors:
            try:
                locator = self._page.locator(selector)
                count = locator.count()

                if inspect.isawaitable(count):
                    continue

            except Exception:
                continue

            for index in range(count):
                try:
                    element = locator.nth(index)

                    visible = element.is_visible()

                    if inspect.isawaitable(visible):
                        continue

                    if not visible:
                        continue

                    field_type = (
                        element.get_attribute("type")
                        or selector
                    )

                    field_id = (
                        element.get_attribute("id")
                        or element.get_attribute("name")
                        or f"field-{field_index}"
                    )

                    label = self._extract_label_sync(
                        element,
                        field_id,
                    )

                    required = (
                        element.get_attribute(
                            "required"
                        )
                        is not None
                    )

                    fields.append(
                        ApplicationFormField(
                            field_id=field_id,
                            label=label,
                            field_type=field_type,
                            required=required,
                        )
                    )

                    field_index += 1

                except Exception:
                    continue

        return fields

    def _extract_label_sync(
        self,
        element: Any,
        field_id: str,
    ) -> str:

        try:
            aria_label = element.get_attribute(
                "aria-label"
            )

            if aria_label:
                return aria_label.strip()

            placeholder = element.get_attribute(
                "placeholder"
            )

            if placeholder:
                return placeholder.strip()

            element_id = element.get_attribute("id")

            if element_id:
                label_locator = self._page.locator(
                    f"label[for='{element_id}']"
                )

                count = label_locator.count()

                if not inspect.isawaitable(count):
                    if count > 0:
                        text = (
                            label_locator.first
                            .inner_text()
                            .strip()
                        )

                        if text:
                            return text

        except Exception:
            pass

        return field_id

    def _company_name_sync(self) -> str | None:
        selectors = (
            ".job-details-jobs-unified-top-card__company-name",
            "[data-testid='job-details-company-name']",
            ".jobs-unified-top-card__company-name",
            "[data-company]",
        )

        for selector in selectors:
            try:
                locator = self._page.locator(selector)

                count = locator.count()

                if inspect.isawaitable(count):
                    continue

                if count == 0:
                    continue

                if selector == "[data-company]":
                    value = locator.first.get_attribute(
                        "data-company"
                    )

                    if inspect.isawaitable(value):
                        continue

                    if value:
                        return value.strip()

                text = (
                    locator.first
                    .inner_text()
                    .strip()
                )

                if text:
                    return text

            except Exception:
                continue

        return None

    # ==============================================================
    # ASYNCHRONOUS PLAYWRIGHT IMPLEMENTATION
    # ==============================================================

    async def _authentication_required_async(
        self,
    ) -> bool:

        selectors = (
            "input[name='session_key']",
            "input[name='session_password']",
            "form[action*='login']",
            "[data-testid='sign-in-form']",
            "[data-login-required='true']",
        )

        return await self._any_selector_visible_async(
            selectors
        )

    async def _captcha_detected_async(
        self,
    ) -> bool:

        selectors = (
            "iframe[src*='captcha']",
            "[id*='captcha']",
            "[class*='captcha']",
            "[data-testid*='captcha']",
            "[data-captcha='true']",
        )

        return await self._any_selector_visible_async(
            selectors
        )

    async def _easy_apply_detected_async(
        self,
    ) -> bool:

        selectors = (
            "button.jobs-apply-button",
            "button[aria-label*='Easy Apply']",
            "button:has-text('Easy Apply')",
            "[data-easy-apply='true']",
        )

        return await self._any_selector_visible_async(
            selectors
        )

    async def _external_application_detected_async(
        self,
    ) -> bool:

        selectors = (
            "a[href*='apply']",
            "button:has-text('Apply')",
            "[data-external-application='true']",
        )

        return await self._any_selector_visible_async(
            selectors
        )

    async def _any_selector_visible_async(
        self,
        selectors: tuple[str, ...],
    ) -> bool:

        for selector in selectors:
            try:
                locator = self._page.locator(
                    selector
                )

                count = await locator.count()

                for index in range(count):
                    element = locator.nth(index)

                    if await element.is_visible():
                        return True

            except Exception:
                continue

        return False

    async def _extract_fields_async(
        self,
    ) -> list[ApplicationFormField]:

        fields: list[ApplicationFormField] = []

        selectors = (
            "input",
            "textarea",
            "select",
        )

        field_index = 0

        for selector in selectors:
            try:
                locator = self._page.locator(
                    selector
                )

                count = await locator.count()

            except Exception:
                continue

            for index in range(count):
                try:
                    element = locator.nth(index)

                    if not await element.is_visible():
                        continue

                    field_type = (
                        await element.get_attribute("type")
                        or selector
                    )

                    field_id = (
                        await element.get_attribute("id")
                        or await element.get_attribute("name")
                        or f"field-{field_index}"
                    )

                    label = await self._extract_label_async(
                        element,
                        field_id,
                    )

                    required = (
                        await element.get_attribute(
                            "required"
                        )
                        is not None
                    )

                    fields.append(
                        ApplicationFormField(
                            field_id=field_id,
                            label=label,
                            field_type=field_type,
                            required=required,
                        )
                    )

                    field_index += 1

                except Exception:
                    continue

        return fields

    async def _extract_label_async(
        self,
        element: Any,
        field_id: str,
    ) -> str:

        try:
            aria_label = await element.get_attribute(
                "aria-label"
            )

            if aria_label:
                return aria_label.strip()

            placeholder = await element.get_attribute(
                "placeholder"
            )

            if placeholder:
                return placeholder.strip()

            element_id = await element.get_attribute(
                "id"
            )

            if element_id:
                label_locator = self._page.locator(
                    f"label[for='{element_id}']"
                )

                if await label_locator.count() > 0:
                    text = (
                        await label_locator.first.inner_text()
                    ).strip()

                    if text:
                        return text

        except Exception:
            pass

        return field_id

    async def _safe_title_async(
        self,
    ) -> str | None:

        try:
            value = self._page.title

            if callable(value):
                value = value()

            if inspect.isawaitable(value):
                value = await value

            value = str(value or "").strip()

            return value or None

        except Exception:
            return None

    async def _company_name_async(
        self,
    ) -> str | None:

        selectors = (
            ".job-details-jobs-unified-top-card__company-name",
            "[data-testid='job-details-company-name']",
            ".jobs-unified-top-card__company-name",
            "[data-company]",
        )

        for selector in selectors:
            try:
                locator = self._page.locator(
                    selector
                )

                if await locator.count() == 0:
                    continue

                if selector == "[data-company]":
                    value = await locator.first.get_attribute(
                        "data-company"
                    )

                    if value:
                        return value.strip()

                text = (
                    await locator.first.inner_text()
                ).strip()

                if text:
                    return text

            except Exception:
                continue

        return None
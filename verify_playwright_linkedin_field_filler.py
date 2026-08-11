"""
Playwright LinkedIn field filler integration test.

Uses a local controlled HTML form.

No live job application is submitted.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
    ApplicationAnswerDecision,
    ApplicationAnswerSource,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling.playwright import (
    PlaywrightLinkedInApplicationFieldFiller,
)


async def main() -> None:
    print()
    print("=" * 70)
    print("PLAYWRIGHT LINKEDIN FIELD FILLER INTEGRATION TEST")
    print("=" * 70)

    html_path = (
        Path("sample_data")
        / "linkedin_application_test_form.html"
    ).resolve()

    async with async_playwright() as playwright:

        print()
        print("[1/8] Starting Chromium...")

        browser = await playwright.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("BROWSER start successful")

        # ----------------------------------------------------------
        # 2/8
        # ----------------------------------------------------------

        print()
        print("[2/8] Loading controlled test form...")

        await page.goto(
            html_path.as_uri()
        )

        assert (
            await page.title()
            == "LinkedIn Application Test Form"
        )

        print("TEST FORM navigation successful")

        filler = PlaywrightLinkedInApplicationFieldFiller(
            page
        )

        # ----------------------------------------------------------
        # 3/8
        # ----------------------------------------------------------

        print()
        print("[3/8] Testing text field...")

        answer = ApplicationAnswer(
            field_id="field-001",
            normalized_field_name="first_name",
            value="Aravind",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Explicit candidate profile value.",
        )

        result = await filler.fill_field(answer)

        assert result.success is True

        assert (
            await page.locator("#field-001").input_value()
            == "Aravind"
        )

        print("TEXT field filling successful")
        print("Value:", result.filled_value)

        # ----------------------------------------------------------
        # 4/8
        # ----------------------------------------------------------

        print()
        print("[4/8] Testing email and phone fields...")

        answers = (
            ApplicationAnswer(
                field_id="field-002",
                normalized_field_name="email",
                value="aravind@example.com",
                decision=ApplicationAnswerDecision.AUTO_ANSWER,
                confidence=1.0,
                source=ApplicationAnswerSource.CANDIDATE_PROFILE,
                reason="Explicit candidate profile value.",
            ),
            ApplicationAnswer(
                field_id="field-003",
                normalized_field_name="phone",
                value="+91 9000000000",
                decision=ApplicationAnswerDecision.AUTO_ANSWER,
                confidence=1.0,
                source=ApplicationAnswerSource.CANDIDATE_PROFILE,
                reason="Explicit candidate profile value.",
            ),
        )

        for answer in answers:
            result = await filler.fill_field(answer)
            assert result.success is True

        assert (
            await page.locator("#field-002").input_value()
            == "aravind@example.com"
        )

        assert (
            await page.locator("#field-003").input_value()
            == "+91 9000000000"
        )

        print("EMAIL/PHONE filling successful")

        # ----------------------------------------------------------
        # 5/8
        # ----------------------------------------------------------

        print()
        print("[5/8] Testing select field...")

        answer = ApplicationAnswer(
            field_id="field-006",
            normalized_field_name="employment_type",
            value="Full-time",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Explicit candidate profile value.",
        )

        result = await filler.fill_field(answer)

        assert result.success is True

        selected = await page.locator(
            "#field-006"
        ).locator(
            "option:checked"
        ).text_content()

        assert selected == "Full-time"

        print("SELECT field filling successful")
        print("Selected:", selected)

        # ----------------------------------------------------------
        # 6/8
        # ----------------------------------------------------------

        print()
        print("[6/8] Testing checkbox...")

        answer = ApplicationAnswer(
            field_id="field-007",
            normalized_field_name="remote_status",
            value="yes",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Explicit candidate profile value.",
        )

        result = await filler.fill_field(answer)

        assert result.success is True

        assert (
            await page.locator("#field-007").is_checked()
        )

        print("CHECKBOX filling successful")

        # ----------------------------------------------------------
        # 7/8
        # ----------------------------------------------------------

        print()
        print("[7/8] Testing MANUAL_REVIEW protection...")

        answer = ApplicationAnswer(
            field_id="field-004",
            normalized_field_name="location",
            value="Hyderabad",
            decision=ApplicationAnswerDecision.MANUAL_REVIEW,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Review required.",
        )

        result = await filler.fill_field(answer)

        assert result.success is False
        assert (
            result.error_code
            == "answer_not_approved"
        )

        assert (
            await page.locator("#field-004").input_value()
            == ""
        )

        print("MANUAL_REVIEW protection successful")
        print("Field was not modified")

        # ----------------------------------------------------------
        # 8/8
        # ----------------------------------------------------------

        print()
        print("[8/8] Testing verification failure handling...")

        # Remove the target element to simulate a missing field.
        await page.locator(
            "#field-005"
        ).evaluate(
            "(element) => element.remove()"
        )

        answer = ApplicationAnswer(
            field_id="field-005",
            normalized_field_name="experience_years",
            value="2.10",
            decision=ApplicationAnswerDecision.AUTO_ANSWER,
            confidence=1.0,
            source=ApplicationAnswerSource.CANDIDATE_PROFILE,
            reason="Explicit candidate profile value.",
        )

        result = await filler.fill_field(answer)

        assert result.success is False
        assert (
            result.error_code
            == "field_not_found"
        )

        print("FIELD NOT FOUND handling successful")
        print("Error:", result.error_code)

        await browser.close()

    print()
    print("=" * 70)
    print("PLAYWRIGHT LINKEDIN FIELD FILLER TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
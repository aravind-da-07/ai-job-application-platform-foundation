"""
Controlled end-to-end test for the LinkedIn browser execution workflow.

This test uses a local HTML page and Playwright. It does not connect
to LinkedIn and does not submit a real application.
"""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswer,
    ApplicationAnswerDecision,
    ApplicationAnswerSource,
    AnswerResolutionResult,
)

from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormType,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.workflow import (
    LinkedInBrowserExecutionWorkflow,
)


TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Company - Data Analyst</title>
</head>
<body>

<div
    data-easy-apply="true"
    data-company="Test Company"
>

<form>

<label for="first_name">First Name</label>
<input
    id="first_name"
    name="first_name"
    type="text"
/>

<label for="email">Email</label>
<input
    id="email"
    name="email"
    type="email"
/>

<button
    type="submit"
    data-submit-button="true"
>
    Submit application
</button>

<div
    data-submission-confirmation="true"
    data-confirmation-id="workflow-confirmation-001"
    style="display:none;"
>
    Application submitted
</div>

</form>

<script>
document.querySelector("form").addEventListener(
    "submit",
    function(event) {
        event.preventDefault();

        const confirmation =
            document.querySelector(
                '[data-submission-confirmation="true"]'
            );

        confirmation.style.display = "block";
    }
);
</script>

</div>

</body>
</html>
"""


def auto_answer(
    field_id: str,
    normalized_name: str,
    value: str,
) -> ApplicationAnswer:
    """Create an approved automatic answer."""

    return ApplicationAnswer(
        field_id=field_id,
        normalized_field_name=normalized_name,
        value=value,
        decision=ApplicationAnswerDecision.AUTO_ANSWER,
        confidence=1.0,
        source=ApplicationAnswerSource.CANDIDATE_PROFILE,
        reason="Controlled workflow test value.",
    )


def manual_answer(
    field_id: str,
    normalized_name: str,
) -> ApplicationAnswer:
    """Create a manual-review answer."""

    return ApplicationAnswer(
        field_id=field_id,
        normalized_field_name=normalized_name,
        value=None,
        decision=ApplicationAnswerDecision.MANUAL_REVIEW,
        confidence=0.5,
        source=ApplicationAnswerSource.UNKNOWN,
        reason="Controlled manual-review test.",
    )


async def test_successful_workflow(page) -> None:
    """Test the complete successful browser workflow."""

    await page.set_content(TEST_HTML)

    resolution = AnswerResolutionResult(
        answers=(
            auto_answer(
                "first_name",
                "first_name",
                "Aravind",
            ),
            auto_answer(
                "email",
                "email",
                "aravind@example.com",
            ),
        ),
        auto_answer_count=2,
        manual_review_count=0,
        skipped_count=0,
    )

    workflow = LinkedInBrowserExecutionWorkflow()

    result = await workflow.execute(
        application_id="browser-workflow-001",
        external_job_id="linkedin-test-001",
        page=page,
        resolution=resolution,
    )

    assert (
        result.form_type
        == ApplicationFormType.EASY_APPLY
    )

    assert result.fields_detected >= 2
    assert result.fields_filled == 2
    assert result.fields_failed == 0

    assert result.submission is not None

    assert result.submission.submitted is True

    assert (
        result.submission.confirmation_id
        == "workflow-confirmation-001"
    )

    assert result.completed is True
    assert result.requires_manual_intervention is False

    print("SUCCESSFUL workflow successful")
    print(
        "Form:",
        result.form_type.value,
    )
    print(
        "Fields detected:",
        result.fields_detected,
    )
    print(
        "Fields filled:",
        result.fields_filled,
    )
    print(
        "Confirmation:",
        result.submission.confirmation_id,
    )


async def test_manual_review_protection(page) -> None:
    """Verify manual review prevents browser execution."""

    await page.set_content(TEST_HTML)

    resolution = AnswerResolutionResult(
        answers=(
            auto_answer(
                "first_name",
                "first_name",
                "Aravind",
            ),
            manual_answer(
                "email",
                "email",
            ),
        ),
        auto_answer_count=1,
        manual_review_count=1,
        skipped_count=0,
    )

    workflow = LinkedInBrowserExecutionWorkflow()

    result = await workflow.execute(
        application_id="browser-workflow-002",
        external_job_id="linkedin-test-002",
        page=page,
        resolution=resolution,
    )

    assert (
        result.form_type
        == ApplicationFormType.EASY_APPLY
    )

    assert result.completed is False
    assert result.requires_manual_intervention is True

    assert result.fields_filled == 0
    assert result.submission is None

    # Browser fields must remain untouched.
    first_name = await page.locator(
        "#first_name"
    ).input_value()

    email = await page.locator(
        "#email"
    ).input_value()

    assert first_name == ""
    assert email == ""

    print("MANUAL REVIEW protection successful")
    print("Fields filled:", result.fields_filled)
    print("Submission attempted:", result.submission is not None)


async def test_authentication_protection(page) -> None:
    """Verify authentication stops execution."""

    authentication_html = """
    <html>
    <body>
        <div data-login-required="true">
            Sign in to continue
        </div>
    </body>
    </html>
    """

    await page.set_content(authentication_html)

    workflow = LinkedInBrowserExecutionWorkflow()

    resolution = AnswerResolutionResult()

    result = await workflow.execute(
        application_id="browser-workflow-003",
        external_job_id="linkedin-test-003",
        page=page,
        resolution=resolution,
    )

    assert (
        result.form_type
        == ApplicationFormType.AUTHENTICATION_REQUIRED
    )

    assert result.completed is False
    assert result.requires_manual_intervention is True

    assert result.submission is None

    print("AUTHENTICATION protection successful")
    print(
        "Form:",
        result.form_type.value,
    )
    print(
        "Error:",
        result.error_code,
    )


async def test_captcha_protection(page) -> None:
    """Verify CAPTCHA stops execution."""

    captcha_html = """
    <html>
    <body>
        <div data-captcha="true">
            CAPTCHA verification required
        </div>
    </body>
    </html>
    """

    await page.set_content(captcha_html)

    workflow = LinkedInBrowserExecutionWorkflow()

    resolution = AnswerResolutionResult()

    result = await workflow.execute(
        application_id="browser-workflow-004",
        external_job_id="linkedin-test-004",
        page=page,
        resolution=resolution,
    )

    assert (
        result.form_type
        == ApplicationFormType.CAPTCHA_DETECTED
    )

    assert result.completed is False
    assert result.requires_manual_intervention is True

    assert result.submission is None

    print("CAPTCHA protection successful")
    print(
        "Form:",
        result.form_type.value,
    )
    print(
        "Error:",
        result.error_code,
    )


async def main() -> None:
    print()
    print("=" * 70)
    print("LINKEDIN BROWSER WORKFLOW INTEGRATION TEST")
    print("=" * 70)

    async with async_playwright() as playwright:
        print()
        print("[1/5] Starting Chromium...")

        browser = await playwright.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("BROWSER start successful")

        print()
        print("[2/5] Testing complete successful workflow...")

        await test_successful_workflow(page)

        print()
        print("[3/5] Testing manual-review protection...")

        await test_manual_review_protection(page)

        print()
        print("[4/5] Testing authentication protection...")

        await test_authentication_protection(page)

        print()
        print("[5/5] Testing CAPTCHA protection...")

        await test_captcha_protection(page)

        await browser.close()

    print()
    print("=" * 70)
    print("LINKEDIN BROWSER WORKFLOW TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
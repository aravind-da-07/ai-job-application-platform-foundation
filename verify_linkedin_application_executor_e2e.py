"""
End-to-end integration test for LinkedInApplicationExecutor.

Uses a controlled local HTML page instead of the real LinkedIn site.

This validates:

    Executor
        -> Form Detector
        -> Field Mapper
        -> Answer Resolver
        -> Execution Planning
        -> Playwright Field Filler
        -> Submission
        -> Confirmation
"""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionRequest,
    ApplicationExecutionStatus,
)
from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormType,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin import (
    LinkedInApplicationExecutor,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.form_detector import (
    LinkedInApplicationFormDetector,
)
from src.shared.config.constants import JobSourceType


# ======================================================================
# CONTROLLED LOCAL TEST PAGE
# ======================================================================

TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn Test Application</title>
</head>

<body>

    <div
        class="job-details-jobs-unified-top-card__company-name"
    >
        Test Company
    </div>

    <button
        class="jobs-apply-button"
        aria-label="Easy Apply"
        type="button"
    >
        Easy Apply
    </button>

    <form id="application-form">

        <label for="first-name">
            First Name
        </label>

        <input
            id="first-name"
            data-field-id="field-first-name"
            aria-label="First Name"
            type="text"
        >

        <label for="email">
            Email
        </label>

        <input
            id="email"
            data-field-id="field-email"
            aria-label="Email Address"
            type="email"
        >

        <button
            type="button"
            data-submit-button="true"
            id="submit-application"
        >
            Submit Application
        </button>

    </form>

    <div
        id="confirmation"
        data-submission-confirmation="true"
        data-confirmation-id="e2e-confirmation-001"
        style="display:none;"
    >
        Application submitted successfully.
    </div>

    <script>
        document
            .getElementById("submit-application")
            .addEventListener("click", function () {

                const firstName =
                    document.getElementById("first-name").value;

                const email =
                    document.getElementById("email").value;

                if (
                    firstName === "Aravind" &&
                    email === "aravind@example.com"
                ) {
                    document
                        .getElementById("confirmation")
                        .style.display = "block";
                }
            });
    </script>

</body>
</html>
"""


# ======================================================================
# REQUEST BUILDER
# ======================================================================

def build_request() -> ApplicationExecutionRequest:
    """Build a valid LinkedIn application request."""

    return ApplicationExecutionRequest(
        application_id="e2e-application-001",
        external_job_id="linkedin-e2e-job-001",
        job_url=(
            "https://www.linkedin.com/jobs/view/"
            "e2e-test"
        ),
        source=JobSourceType.LINKEDIN,
        candidate_data={
            "first_name": "Aravind",
            "email": "aravind@example.com",
        },
    )


# ======================================================================
# TEST 2 — COMPLETE EXECUTOR FLOW
# ======================================================================

async def test_successful_executor_flow(page) -> None:
    print("\n[2/6] Testing complete executor flow...")

    await page.set_content(TEST_HTML)

    # --------------------------------------------------------------
    # Verify form detection independently.
    # --------------------------------------------------------------

    detector = LinkedInApplicationFormDetector(page)

    snapshot = await detector.detect_async()

    print(
        "DEBUG FORM TYPE:",
        snapshot.form_type.value,
    )

    print(
        "DEBUG FORM DETECTED:",
        snapshot.detected,
    )

    print(
        "DEBUG FIELD COUNT:",
        len(snapshot.fields),
    )

    print(
        "DEBUG COMPANY:",
        snapshot.company_name,
    )

    assert (
        snapshot.form_type
        == ApplicationFormType.EASY_APPLY
    )

    assert snapshot.detected is True

    assert len(snapshot.fields) == 2

    # --------------------------------------------------------------
    # Create executor.
    # --------------------------------------------------------------

    executor = LinkedInApplicationExecutor(
        browser_session=page
    )

    assert executor.configured is True

    # --------------------------------------------------------------
    # Execute complete workflow.
    # --------------------------------------------------------------

    result = await executor.execute_async(
        build_request()
    )

    # --------------------------------------------------------------
    # Diagnostic output.
    # --------------------------------------------------------------

    print(
        "DEBUG EXECUTOR STATUS:",
        result.status.value,
    )

    print(
        "DEBUG SUBMITTED:",
        result.submitted,
    )

    print(
        "DEBUG MANUAL INTERVENTION:",
        result.requires_manual_intervention,
    )

    print(
        "DEBUG REASON:",
        result.reason,
    )

    print(
        "DEBUG ERROR CODE:",
        result.error_code,
    )

    print(
        "DEBUG FIELDS DETECTED:",
        result.fields_detected,
    )

    print(
        "DEBUG FIELDS FILLED:",
        result.fields_filled,
    )

    print(
        "DEBUG METADATA:",
        result.metadata,
    )

    # --------------------------------------------------------------
    # Final success boundary.
    # --------------------------------------------------------------

    assert (
        result.status
        == ApplicationExecutionStatus.SUBMITTED
    ), (
        "Expected SUBMITTED, "
        f"got {result.status.value}; "
        f"reason={result.reason}; "
        f"error_code={result.error_code}; "
        f"metadata={result.metadata}"
    )

    assert result.submitted is True

    assert (
        result.requires_manual_intervention
        is False
    )

    assert result.fields_detected == 2

    assert result.fields_filled == 2

    # --------------------------------------------------------------
    # Confirmation.
    # --------------------------------------------------------------

    confirmation_id = result.metadata.get(
        "confirmation_id"
    )

    assert (
        confirmation_id
        == "e2e-confirmation-001"
    )

    # --------------------------------------------------------------
    # Verify browser values.
    # --------------------------------------------------------------

    first_name = await page.locator(
        "#first-name"
    ).input_value()

    email = await page.locator(
        "#email"
    ).input_value()

    assert first_name == "Aravind"

    assert email == "aravind@example.com"

    # --------------------------------------------------------------
    # Verify confirmation marker.
    # --------------------------------------------------------------

    confirmation = page.locator(
        '[data-submission-confirmation="true"]'
    ).first

    assert await confirmation.is_visible()

    print(
        "EXECUTOR end-to-end flow successful"
    )

    print(
        "Status:",
        result.status.value,
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
        confirmation_id,
    )


# ======================================================================
# TEST 3 — AUTHENTICATION PROTECTION
# ======================================================================

async def test_authentication_protection(page) -> None:
    print(
        "\n[3/6] Testing authentication protection..."
    )

    html = """
    <!DOCTYPE html>
    <html>
    <body>

        <form action="/login">

            <input
                name="session_key"
                type="text"
            >

            <input
                name="session_password"
                type="password"
            >

        </form>

    </body>
    </html>
    """

    await page.set_content(html)

    executor = LinkedInApplicationExecutor(
        browser_session=page
    )

    result = await executor.execute_async(
        build_request()
    )

    assert result.submitted is False

    assert (
        result.status
        == ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert (
        result.error_code
        == "authentication_required"
    )

    print(
        "AUTHENTICATION protection successful"
    )

    print(
        "Status:",
        result.status.value,
    )

    print(
        "Error:",
        result.error_code,
    )


# ======================================================================
# TEST 4 — CAPTCHA PROTECTION
# ======================================================================

async def test_captcha_protection(page) -> None:
    print(
        "\n[4/6] Testing CAPTCHA protection..."
    )

    html = """
    <!DOCTYPE html>
    <html>
    <body>

        <div id="captcha">
            CAPTCHA TEST
        </div>

    </body>
    </html>
    """

    await page.set_content(html)

    executor = LinkedInApplicationExecutor(
        browser_session=page
    )

    result = await executor.execute_async(
        build_request()
    )

    assert result.submitted is False

    assert (
        result.status
        == ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert (
        result.error_code
        == "captcha_detected"
    )

    print(
        "CAPTCHA protection successful"
    )

    print(
        "Status:",
        result.status.value,
    )

    print(
        "Error:",
        result.error_code,
    )


# ======================================================================
# TEST 5 — MISSING CANDIDATE ANSWER
# ======================================================================

async def test_missing_candidate_answer(page) -> None:
    print(
        "\n[5/6] Testing missing candidate answer..."
    )

    html = """
    <!DOCTYPE html>
    <html>
    <body>

        <button
            class="jobs-apply-button"
            aria-label="Easy Apply"
            type="button"
        >
            Easy Apply
        </button>

        <input
            id="first-name"
            data-field-id="field-first-name"
            aria-label="First Name"
            type="text"
        >

        <input
            id="email"
            data-field-id="field-email"
            aria-label="Email Address"
            type="email"
        >

        <button
            type="button"
            data-submit-button="true"
        >
            Submit
        </button>

    </body>
    </html>
    """

    await page.set_content(html)

    executor = LinkedInApplicationExecutor(
        browser_session=page
    )

    request = ApplicationExecutionRequest(
        application_id="e2e-missing-answer",
        external_job_id="linkedin-e2e-job-002",
        job_url=(
            "https://www.linkedin.com/jobs/view/"
            "e2e-test-2"
        ),
        source=JobSourceType.LINKEDIN,
        candidate_data={
            "first_name": "Aravind",
        },
    )

    result = await executor.execute_async(
        request
    )

    print(
        "DEBUG MISSING ANSWER STATUS:",
        result.status.value,
    )

    print(
        "DEBUG MISSING ANSWER REASON:",
        result.reason,
    )

    print(
        "DEBUG MISSING ANSWER ERROR:",
        result.error_code,
    )

    assert result.submitted is False

    assert (
        result.status
        == ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert result.requires_manual_intervention is True

    print(
        "MISSING ANSWER protection successful"
    )

    print(
        "Status:",
        result.status.value,
    )

    print(
        "Fields filled:",
        result.fields_filled,
    )


# ======================================================================
# TEST 6 — REQUEST VALIDATION
# ======================================================================

async def test_invalid_application_request(page) -> None:
    print(
        "\n[6/6] Testing request validation..."
    )

    executor = LinkedInApplicationExecutor(
        browser_session=page
    )

    # --------------------------------------------------------------
    # IMPORTANT:
    #
    # ApplicationExecutionRequest validates itself inside its
    # constructor. Therefore the request must be created INSIDE
    # the try/except block.
    # --------------------------------------------------------------

    try:

        ApplicationExecutionRequest(
            application_id="",
            external_job_id="linkedin-e2e-invalid",
            job_url=(
                "https://www.linkedin.com/jobs/view/"
                "test"
            ),
            source=JobSourceType.LINKEDIN,
            candidate_data={},
        )

    except ValueError as exc:

        assert (
            str(exc)
            == "application_id cannot be empty."
        )

        print(
            "REQUEST validation successful"
        )

        print(
            "Expected error:",
            exc,
        )

        return

    raise AssertionError(
        "Expected application_id validation error."
    )


# ======================================================================
# MAIN
# ======================================================================

async def main() -> None:

    print("=" * 70)

    print(
        "LINKEDIN APPLICATION EXECUTOR "
        "END-TO-END TEST"
    )

    print("=" * 70)

    async with async_playwright() as playwright:

        # ----------------------------------------------------------
        # Test 1 — Browser
        # ----------------------------------------------------------

        print(
            "\n[1/6] Starting Chromium..."
        )

        browser = await playwright.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print(
            "BROWSER start successful"
        )

        try:

            # ------------------------------------------------------
            # Test 2
            # ------------------------------------------------------

            await test_successful_executor_flow(
                page
            )

            # ------------------------------------------------------
            # Test 3
            # ------------------------------------------------------

            await test_authentication_protection(
                page
            )

            # ------------------------------------------------------
            # Test 4
            # ------------------------------------------------------

            await test_captcha_protection(
                page
            )

            # ------------------------------------------------------
            # Test 5
            # ------------------------------------------------------

            await test_missing_candidate_answer(
                page
            )

            # ------------------------------------------------------
            # Test 6
            # ------------------------------------------------------

            await test_invalid_application_request(
                page
            )

        finally:

            await browser.close()

    print(
        "\n" + "=" * 70
    )

    print(
        "LINKEDIN APPLICATION EXECUTOR "
        "E2E TEST PASSED"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    asyncio.run(main())
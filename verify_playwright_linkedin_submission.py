"""
Playwright LinkedIn submission integration test.

Uses a controlled local HTML page.

No real application is submitted.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from src.modules.job_discovery.domain.application_executor.submission import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionStatus,
)

from src.modules.job_discovery.infrastructure.application_executor.linkedin.submission import (
    PlaywrightLinkedInApplicationSubmitter,
)


async def load_page(page, html_file: Path) -> None:
    """Load a local test page."""

    await page.goto(html_file.as_uri())


def create_request(
    application_id: str,
    external_job_id: str,
    verified_field_count: int = 5,
) -> ApplicationSubmissionRequest:
    """Create a valid submission request."""

    return ApplicationSubmissionRequest(
        application_id=application_id,
        external_job_id=external_job_id,
        verified_field_count=verified_field_count,
    )


async def main() -> None:
    print()
    print("=" * 70)
    print("PLAYWRIGHT LINKEDIN SUBMISSION INTEGRATION TEST")
    print("=" * 70)

    html_path = (
        Path("sample_data")
        / "linkedin_submission_test_form.html"
    ).resolve()

    async with async_playwright() as playwright:

        print()
        print("[1/6] Starting Chromium...")

        browser = await playwright.chromium.launch(
            headless=True
        )

        print("BROWSER start successful")

        # ==========================================================
        # 2/6
        # ==========================================================

        print()
        print("[2/6] Testing successful submission...")

        page = await browser.new_page()

        await load_page(
            page,
            html_path,
        )

        submitter = PlaywrightLinkedInApplicationSubmitter(
            page
        )

        result = await submitter.submit(
            create_request(
                "submit-test-001",
                "job-001",
                8,
            )
        )

        assert (
            result.status
            == ApplicationSubmissionStatus.SUBMITTED
        )

        assert result.submitted is True

        assert (
            result.confirmation_id
            == "test-confirmation-001"
        )

        assert result.verified_field_count == 8

        print("SUCCESSFUL submission successful")
        print("Status:", result.status.value)
        print("Submitted:", result.submitted)
        print("Confirmation:", result.confirmation_id)

        await page.close()

        # ==========================================================
        # 3/6
        # ==========================================================

        print()
        print("[3/6] Testing missing submit button...")

        page = await browser.new_page()

        await page.set_content(
            """
            <html>
            <body>
                <h1>No Submit Button</h1>
            </body>
            </html>
            """
        )

        submitter = PlaywrightLinkedInApplicationSubmitter(
            page
        )

        result = await submitter.submit(
            create_request(
                "submit-test-002",
                "job-002",
            )
        )

        assert (
            result.status
            == ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED
        )

        assert result.submitted is False

        assert (
            result.error_code
            == "submit_button_not_found"
        )

        print("MISSING BUTTON handling successful")
        print("Status:", result.status.value)
        print("Error:", result.error_code)

        await page.close()

        # ==========================================================
        # 4/6
        # ==========================================================

        print()
        print("[4/6] Testing missing confirmation...")

        page = await browser.new_page()

        await page.set_content(
            """
            <html>
            <body>

            <button
                type="button"
                data-submit-button="true"
                onclick="document.body.setAttribute(
                    'data-clicked',
                    'true'
                )"
            >
                Submit
            </button>

            </body>
            </html>
            """
        )

        submitter = PlaywrightLinkedInApplicationSubmitter(
            page
        )

        result = await submitter.submit(
            create_request(
                "submit-test-003",
                "job-003",
            )
        )

        assert (
            result.status
            == ApplicationSubmissionStatus.FAILED
        )

        assert result.submitted is False

        assert (
            result.error_code
            == "submission_confirmation_not_detected"
        )

        print("MISSING CONFIRMATION handling successful")
        print("Status:", result.status.value)
        print("Error:", result.error_code)

        await page.close()

        # ==========================================================
        # 5/6
        # ==========================================================

        print()
        print("[5/6] Testing confirmation without ID...")

        page = await browser.new_page()

        await page.set_content(
            """
            <html>
            <body>

            <button
                type="button"
                data-submit-button="true"
            >
                Submit
            </button>

            <div
                data-submission-confirmation="true"
                style="display: none;"
            >
                Submitted
            </div>

            <script>
                document
                    .querySelector(
                        '[data-submit-button="true"]'
                    )
                    .addEventListener(
                        'click',
                        function () {
                            document
                                .querySelector(
                                    '[data-submission-confirmation="true"]'
                                )
                                .style.display = "block";
                        }
                    );
            </script>

            </body>
            </html>
            """
        )

        submitter = PlaywrightLinkedInApplicationSubmitter(
            page
        )

        result = await submitter.submit(
            create_request(
                "submit-test-004",
                "job-004",
            )
        )

        assert (
            result.status
            == ApplicationSubmissionStatus.FAILED
        )

        assert result.submitted is False

        assert (
            result.error_code
            == "confirmation_id_missing"
        )

        print("CONFIRMATION ID protection successful")
        print("Status:", result.status.value)
        print("Error:", result.error_code)

        await page.close()

        # ==========================================================
        # 6/6
        # ==========================================================

        print()
        print("[6/6] Testing disabled submit button...")

        page = await browser.new_page()

        await page.set_content(
            """
            <html>
            <body>

            <button
                type="button"
                data-submit-button="true"
                disabled
            >
                Submit
            </button>

            </body>
            </html>
            """
        )

        submitter = PlaywrightLinkedInApplicationSubmitter(
            page
        )

        result = await submitter.submit(
            create_request(
                "submit-test-005",
                "job-005",
            )
        )

        assert (
            result.status
            == ApplicationSubmissionStatus.MANUAL_REVIEW_REQUIRED
        )

        assert result.submitted is False

        assert (
            result.error_code
            == "submit_button_disabled"
        )

        print("DISABLED BUTTON handling successful")
        print("Status:", result.status.value)
        print("Error:", result.error_code)

        await page.close()

        await browser.close()

    print()
    print("=" * 70)
    print("PLAYWRIGHT LINKEDIN SUBMISSION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
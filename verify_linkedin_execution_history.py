"""
LinkedIn application execution history integration test.

Verifies that normalized LinkedIn execution results are correctly
recorded in the application execution history repository.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from playwright.async_api import async_playwright

from src.modules.job_discovery.domain.application_executor import (
    ApplicationExecutionRequest,
    ApplicationExecutionStatus,
)
from src.modules.job_discovery.domain.application_executor.history import (
    ApplicationExecutionHistoryStatus,
)
from src.modules.job_discovery.infrastructure.application_executor.history import (
    InMemoryApplicationExecutionHistoryRepository,
)
from src.modules.job_discovery.infrastructure.application_executor.linkedin import (
    LinkedInApplicationExecutor,
)
from src.shared.config.constants import JobSourceType


TEST_FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn History Test</title>
</head>
<body>

<div data-testid="job-details-company-name">
    Test Company
</div>

<button
    class="jobs-apply-button"
    data-easy-apply="true"
>
    Easy Apply
</button>

<form>

    <input
        id="first-name"
        data-field-id="field-001"
        aria-label="First Name"
        type="text"
    />

    <input
        id="email"
        data-field-id="field-002"
        aria-label="Email"
        type="email"
    />

    <button
        type="button"
        data-submit-button="true"
        onclick="
            document
                .querySelector(
                    '[data-submission-confirmation=true]'
                )
                .style.display='block';
        "
    >
        Submit
    </button>

    <div
        data-submission-confirmation="true"
        data-confirmation-id="history-confirmation-001"
        style="display:none;"
    >
        Application submitted
    </div>

</form>

</body>
</html>
"""


AUTHENTICATION_HTML = """
<!DOCTYPE html>
<html>
<body>

<form action="/login">
    <input name="session_key" />
    <input name="session_password" />
</form>

</body>
</html>
"""


CAPTCHA_HTML = """
<!DOCTYPE html>
<html>
<body>

<div id="captcha">
    CAPTCHA challenge
</div>

</body>
</html>
"""


async def create_executor(
    page,
    repository,
) -> LinkedInApplicationExecutor:
    """
    Create an executor configured with the test browser page
    and execution history repository.
    """

    return LinkedInApplicationExecutor(
        browser_session=page,
        history_repository=repository,
    )


def build_request(
    *,
    application_id: str,
    candidate_data: dict,
) -> ApplicationExecutionRequest:
    return ApplicationExecutionRequest(
        application_id=application_id,
        external_job_id="linkedin-history-job-001",
        job_url="https://www.linkedin.com/jobs/view/test",
        source=JobSourceType.LINKEDIN,
        candidate_data=candidate_data,
    )


async def test_successful_submission(
    page,
) -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    executor = await create_executor(
        page,
        repository,
    )

    await page.set_content(
        TEST_FORM_HTML
    )

    request = build_request(
        application_id="history-app-001",
        candidate_data={
            "first_name": "Aravind",
            "email": "aravind@example.com",
        },
    )

    result = await executor.execute_async(
        request
    )

    assert result.status == (
        ApplicationExecutionStatus.SUBMITTED
    )

    assert result.submitted is True

    history = repository.get_latest(
        "history-app-001"
    )

    assert history is not None

    assert history.status == (
        ApplicationExecutionHistoryStatus.SUBMITTED
    )

    assert history.confirmation_id == (
        "history-confirmation-001"
    )

    assert history.fields_detected == 2
    assert history.fields_filled == 2

    assert history.manual_intervention_required is False

    print(
        "SUCCESS history recording successful"
    )
    print(
        f"Status: {history.status.value}"
    )
    print(
        f"Confirmation: {history.confirmation_id}"
    )


async def test_authentication_history(
    page,
) -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    executor = await create_executor(
        page,
        repository,
    )

    await page.set_content(
        AUTHENTICATION_HTML
    )

    request = build_request(
        application_id="history-app-002",
        candidate_data={},
    )

    result = await executor.execute_async(
        request
    )

    assert result.status == (
        ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert result.error_code == (
        "authentication_required"
    )

    history = repository.get_latest(
        "history-app-002"
    )

    assert history is not None

    assert history.status == (
        ApplicationExecutionHistoryStatus
        .MANUAL_REVIEW_REQUIRED
    )

    assert history.manual_intervention_required is True

    assert history.error_code == (
        "authentication_required"
    )

    print(
        "AUTHENTICATION history recording successful"
    )


async def test_captcha_history(
    page,
) -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    executor = await create_executor(
        page,
        repository,
    )

    await page.set_content(
        CAPTCHA_HTML
    )

    request = build_request(
        application_id="history-app-003",
        candidate_data={},
    )

    result = await executor.execute_async(
        request
    )

    assert result.status == (
        ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert result.error_code == (
        "captcha_detected"
    )

    history = repository.get_latest(
        "history-app-003"
    )

    assert history is not None

    assert history.status == (
        ApplicationExecutionHistoryStatus
        .MANUAL_REVIEW_REQUIRED
    )

    assert history.manual_intervention_required is True

    assert history.error_code == (
        "captcha_detected"
    )

    print(
        "CAPTCHA history recording successful"
    )


async def test_missing_answer_history(
    page,
) -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    executor = await create_executor(
        page,
        repository,
    )

    await page.set_content(
        TEST_FORM_HTML
    )

    request = build_request(
        application_id="history-app-004",
        candidate_data={
            "first_name": "Aravind",
        },
    )

    result = await executor.execute_async(
        request
    )

    assert result.status == (
        ApplicationExecutionStatus.MANUAL_REVIEW_REQUIRED
    )

    assert result.submitted is False

    assert result.error_code == (
        "execution_blocked"
    )

    history = repository.get_latest(
        "history-app-004"
    )

    assert history is not None

    assert history.status == (
        ApplicationExecutionHistoryStatus
        .MANUAL_REVIEW_REQUIRED
    )

    assert history.manual_intervention_required is True

    assert history.error_code == (
        "execution_blocked"
    )

    assert history.fields_filled == 0

    print(
        "MISSING ANSWER history recording successful"
    )


async def test_browser_failure_history(
    page,
) -> None:
    repository = (
        InMemoryApplicationExecutionHistoryRepository()
    )

    executor = await create_executor(
        page,
        repository,
    )

    await page.set_content(
        TEST_FORM_HTML
    )

    # Deliberately provide a page that will cause browser
    # execution to fail after the application has been detected.
    await page.evaluate(
        """
        () => {
            const submit =
                document.querySelector(
                    '[data-submit-button="true"]'
                );

            if (submit) {
                submit.remove();
            }
        }
        """
    )

    request = build_request(
        application_id="history-app-005",
        candidate_data={
            "first_name": "Aravind",
            "email": "aravind@example.com",
        },
    )

    result = await executor.execute_async(
        request
    )

    history = repository.get_latest(
        "history-app-005"
    )

    assert history is not None

    if result.status == ApplicationExecutionStatus.FAILED:
        assert history.status == (
            ApplicationExecutionHistoryStatus.FAILED
        )

        assert history.manual_intervention_required is True

        print(
            "BROWSER FAILURE history recording successful"
        )
    else:
        # The workflow may normalize a missing submit button
        # as manual review rather than an execution failure.
        assert history.status == (
            ApplicationExecutionHistoryStatus
            .MANUAL_REVIEW_REQUIRED
        )

        assert history.manual_intervention_required is True

        print(
            "BROWSER FAILURE safety history recording successful"
        )


async def test_history_failure_isolation(
    page,
) -> None:
    class FailingHistoryRepository:
        def save(self, history):
            raise RuntimeError(
                "simulated_history_repository_failure"
            )

        def get_by_application_id(
            self,
            application_id,
        ):
            return ()

        def get_latest(
            self,
            application_id,
        ):
            return None

    repository = FailingHistoryRepository()

    executor = await create_executor(
        page,
        repository,
    )

    await page.set_content(
        TEST_FORM_HTML
    )

    request = build_request(
        application_id="history-app-006",
        candidate_data={
            "first_name": "Aravind",
            "email": "aravind@example.com",
        },
    )

    result = await executor.execute_async(
        request
    )

    assert result.status == (
        ApplicationExecutionStatus.SUBMITTED
    )

    assert result.submitted is True

    print(
        "HISTORY FAILURE isolation successful"
    )
    print(
        "Execution result remained SUBMITTED"
    )


async def main() -> None:
    print("=" * 70)
    print(
        "LINKEDIN APPLICATION EXECUTION HISTORY "
        "INTEGRATION TEST"
    )
    print("=" * 70)

    async with async_playwright() as playwright:

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

            print(
                "\n[2/6] Testing successful submission "
                "history..."
            )

            await test_successful_submission(
                page
            )

            print(
                "\n[3/6] Testing authentication history..."
            )

            await test_authentication_history(
                page
            )

            print(
                "\n[4/6] Testing CAPTCHA history..."
            )

            await test_captcha_history(
                page
            )

            print(
                "\n[5/6] Testing missing-answer and "
                "browser-failure history..."
            )

            await test_missing_answer_history(
                page
            )

            await test_browser_failure_history(
                page
            )

            print(
                "\n[6/6] Testing history persistence "
                "failure isolation..."
            )

            await test_history_failure_isolation(
                page
            )

        finally:
            await browser.close()

    print("\n" + "=" * 70)
    print(
        "LINKEDIN APPLICATION EXECUTION HISTORY "
        "TEST PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
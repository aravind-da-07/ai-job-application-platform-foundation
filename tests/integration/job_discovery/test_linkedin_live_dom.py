"""
Integration tests for LinkedIn live-DOM extraction.

These tests use a local HTML document rendered by Chromium.
They do not connect to LinkedIn and do not require LinkedIn credentials.

The purpose is to verify:

    HTML
      ↓
    Playwright
      ↓
    PlaywrightPortalSession
      ↓
    LinkedInJobCardExtractor
      ↓
    DiscoveredJob
"""

from __future__ import annotations

from pathlib import Path

from src.modules.job_discovery.infrastructure.browser.playwright_portal_session import (
    PlaywrightPortalSession,
)
from src.modules.job_discovery.infrastructure.portals.linkedin.linkedin_search import (
    LinkedInJobCardExtractor,
)
from src.shared.browser.browser_engine import BrowserEngine


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn Jobs Test</title>
</head>
<body>

    <ul class="jobs-search__results-list">

        <li class="base-card">
            <a
                class="base-card__full-link"
                href="https://www.linkedin.com/jobs/view/123456789/"
            >
                View job
            </a>

            <h3 class="base-search-card__title">
                Senior Data Analyst
            </h3>

            <h4 class="base-search-card__subtitle">
                Example Analytics Ltd
            </h4>

            <div class="job-search-card__location">
                Hyderabad, Telangana, India
            </div>
        </li>

        <li class="base-card">
            <a
                class="base-card__full-link"
                href="https://www.linkedin.com/jobs/view/987654321/"
            >
                View job
            </a>

            <h3 class="base-search-card__title">
                Business Analyst
            </h3>

            <h4 class="base-search-card__subtitle">
                Example Technologies
            </h4>

            <div class="job-search-card__location">
                Bengaluru, Karnataka, India
            </div>
        </li>

    </ul>

</body>
</html>
"""


def _write_test_html(tmp_path: Path) -> Path:
    """Write the deterministic LinkedIn-like HTML document."""

    html_file = tmp_path / "linkedin_jobs.html"

    html_file.write_text(
        HTML,
        encoding="utf-8",
    )

    return html_file


def test_linkedin_live_dom_is_extracted(
    tmp_path: Path,
) -> None:
    """
    Verify that Chromium + PlaywrightPortalSession + LinkedIn extractor
    can extract realistic LinkedIn-style job cards.
    """

    html_file = _write_test_html(
        tmp_path
    )

    engine = BrowserEngine()

    try:
        engine.start()

        with PlaywrightPortalSession(
            engine
        ) as session:

            session.navigate(
                html_file.resolve().as_uri()
            )

            extractor = LinkedInJobCardExtractor()

            jobs = extractor.extract(
                session,
                maximum_results=10,
            )

        assert len(jobs) == 2

        first_job = jobs[0]

        assert first_job.external_id == (
            "123456789"
        )

        assert first_job.title == (
            "Senior Data Analyst"
        )

        assert first_job.company_name == (
            "Example Analytics Ltd"
        )

        assert first_job.location == (
            "Hyderabad, Telangana, India"
        )

        assert first_job.url == (
            "https://www.linkedin.com/jobs/view/123456789/"
        )

        second_job = jobs[1]

        assert second_job.external_id == (
            "987654321"
        )

        assert second_job.title == (
            "Business Analyst"
        )

        assert second_job.company_name == (
            "Example Technologies"
        )

        assert second_job.location == (
            "Bengaluru, Karnataka, India"
        )

        assert second_job.url == (
            "https://www.linkedin.com/jobs/view/987654321/"
        )

        assert first_job.metadata["portal"] == (
            "LinkedIn"
        )

        assert first_job.metadata["extraction_mode"] == (
            "live"
        )

    finally:
        engine.shutdown()


def test_linkedin_live_dom_respects_maximum_results(
    tmp_path: Path,
) -> None:
    """
    Verify that the extractor respects the requested result limit.
    """

    html_file = _write_test_html(
        tmp_path
    )

    engine = BrowserEngine()

    try:
        engine.start()

        with PlaywrightPortalSession(
            engine
        ) as session:

            session.navigate(
                html_file.resolve().as_uri()
            )

            extractor = LinkedInJobCardExtractor()

            jobs = extractor.extract(
                session,
                maximum_results=1,
            )

        assert len(jobs) == 1

        assert jobs[0].external_id == (
            "123456789"
        )

    finally:
        engine.shutdown()
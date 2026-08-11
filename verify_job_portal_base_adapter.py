"""
Base Job Portal Adapter integration test.

Validates the reusable infrastructure layer without connecting
to a real external job portal.

Architecture tested:

    JobPortal
        |
        v
    BaseJobPortalAdapter
        |
        v
    PortalSession
"""

from __future__ import annotations

from typing import Any

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    PortalSession,
)
from src.modules.job_discovery.infrastructure.portals import (
    BaseJobPortalAdapter,
)
from src.shared.config.constants import JobSourceType


# ----------------------------------------------------------------------
# Fake PortalSession
# ----------------------------------------------------------------------


class FakePortalSession:
    """
    Minimal in-memory PortalSession implementation.

    This test does not require Playwright because the purpose is to
    validate the BaseJobPortalAdapter independently.
    """

    def __init__(self) -> None:
        self._current_url = "about:blank"

        self._texts: dict[str, str] = {
            "#status": "ready",
        }

        self.clicked_selectors: list[str] = []
        self.navigated_urls: list[str] = []

    def navigate(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> None:
        self._current_url = url
        self.navigated_urls.append(url)

    def current_url(self) -> str:
        return self._current_url

    def get_text(
        self,
        selector: str,
    ) -> str:
        return self._texts.get(
            selector,
            "",
        )

    def click(
        self,
        selector: str,
    ) -> None:
        self.clicked_selectors.append(
            selector
        )


# ----------------------------------------------------------------------
# Test adapter
# ----------------------------------------------------------------------


class TestPortalAdapter(BaseJobPortalAdapter):
    """
    Minimal concrete adapter used only for integration testing.
    """

    @property
    def source(self) -> JobSourceType:
        return JobSourceType.LINKEDIN

    @property
    def name(self) -> str:
        return "Test LinkedIn Adapter"

    def is_authenticated(
        self,
        session: PortalSession,
    ) -> bool:
        self._validate_session(session)

        return (
            "linkedin.com"
            in session.current_url()
        )

    def authenticate(
        self,
        session: PortalSession,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._validate_session(session)

        self.open_home(
            session
        )

    def discover_jobs(
        self,
        session: PortalSession,
        criteria: JobSearchCriteria,
    ) -> DiscoveryResult:
        self._validate_session(
            session
        )

        self._validate_criteria(
            criteria
        )

        # IMPORTANT:
        # These field names exactly match the current
        # DiscoveredJob domain entity:
        #
        # external_id
        # title
        # company_name
        # source
        # url
        # location

        job = DiscoveredJob(
            external_id="test-001",
            title="Data Analyst",
            company_name="Test Company",
            source=self.source,
            url=(
                "https://www.linkedin.com/"
                "jobs/view/test-001"
            ),
            location="Hyderabad",
        )

        return DiscoveryResult(
            source=self.source,
            jobs=(job,),
            total_found=1,
        )


# ----------------------------------------------------------------------
# Integration test
# ----------------------------------------------------------------------


def main() -> None:
    print()
    print("=" * 70)
    print("BASE JOB PORTAL ADAPTER INTEGRATION TEST")
    print("=" * 70)

    # --------------------------------------------------------------
    # 1. Create adapter
    # --------------------------------------------------------------

    print()
    print("[1/10] Creating base portal adapter...")

    adapter = TestPortalAdapter(
        base_url="https://www.linkedin.com"
    )

    assert adapter.name == "Test LinkedIn Adapter"

    assert (
        adapter.source
        == JobSourceType.LINKEDIN
    )

    assert (
        adapter.base_url
        == "https://www.linkedin.com"
    )

    print("ADAPTER CREATION successful")
    print(f"Name: {adapter.name}")
    print(f"Source: {adapter.source.value}")
    print(f"Base URL: {adapter.base_url}")

    # --------------------------------------------------------------
    # 2. PortalSession compatibility
    # --------------------------------------------------------------

    print()
    print("[2/10] Testing PortalSession compatibility...")

    session = FakePortalSession()

    assert isinstance(
        session,
        PortalSession,
    )

    print("PORTAL SESSION compatibility successful")
    print("Implements PortalSession: True")

    # --------------------------------------------------------------
    # 3. Home navigation
    # --------------------------------------------------------------

    print()
    print("[3/10] Testing portal home navigation...")

    adapter.open_home(
        session
    )

    assert (
        session.current_url()
        == "https://www.linkedin.com"
    )

    print("HOME NAVIGATION successful")
    print(
        f"Current URL: {session.current_url()}"
    )

    # --------------------------------------------------------------
    # 4. Portal detection
    # --------------------------------------------------------------

    print()
    print("[4/10] Testing portal URL detection...")

    assert adapter.is_on_portal(
        session
    )

    print("PORTAL DETECTION successful")
    print(
        "Current session belongs to portal: True"
    )

    # --------------------------------------------------------------
    # 5. Search criteria validation
    # --------------------------------------------------------------

    print()
    print("[5/10] Testing search criteria validation...")

    criteria = JobSearchCriteria(
        keywords=(
            "Data Analyst",
            "Business Analyst",
        ),
        locations=(
            "Hyderabad",
            "Remote",
        ),
        maximum_results=25,
    )

    adapter._validate_criteria(
        criteria
    )

    assert (
        criteria.maximum_results == 25
    )

    print("SEARCH CRITERIA validation successful")
    print(
        f"Keywords: {criteria.keywords}"
    )
    print(
        f"Locations: {criteria.locations}"
    )
    print(
        f"Maximum results: "
        f"{criteria.maximum_results}"
    )

    # --------------------------------------------------------------
    # 6. Metadata merging
    # --------------------------------------------------------------

    print()
    print("[6/10] Testing metadata merging...")

    base_metadata = {
        "source": "integration_test",
        "attempt": 1,
    }

    additional_metadata = {
        "portal": "linkedin",
        "attempt": 2,
    }

    merged = adapter.merge_metadata(
        base_metadata,
        additional_metadata,
    )

    assert merged == {
        "source": "integration_test",
        "attempt": 2,
        "portal": "linkedin",
    }

    # Ensure source dictionaries were not modified.
    assert (
        base_metadata["attempt"]
        == 1
    )

    assert (
        "portal"
        not in base_metadata
    )

    print("METADATA MERGING successful")
    print(
        f"Merged metadata: {merged}"
    )

    # --------------------------------------------------------------
    # 7. Authentication state
    # --------------------------------------------------------------

    print()
    print("[7/10] Testing authentication state...")

    assert adapter.is_authenticated(
        session
    )

    print("AUTHENTICATION STATE successful")
    print("Authenticated: True")

    # --------------------------------------------------------------
    # 8. Job discovery
    # --------------------------------------------------------------

    print()
    print("[8/10] Testing job discovery...")

    result = adapter.discover_jobs(
        session,
        criteria,
    )

    assert (
        result.source
        == JobSourceType.LINKEDIN
    )

    assert len(result.jobs) == 1

    assert result.total_found == 1

    discovered_job = result.jobs[0]

    assert (
        discovered_job.external_id
        == "test-001"
    )

    assert (
        discovered_job.title
        == "Data Analyst"
    )

    assert (
        discovered_job.company_name
        == "Test Company"
    )

    assert (
        discovered_job.source
        == JobSourceType.LINKEDIN
    )

    assert (
        discovered_job.url
        == "https://www.linkedin.com/"
        "jobs/view/test-001"
    )

    assert (
        discovered_job.location
        == "Hyderabad"
    )

    print("JOB DISCOVERY successful")
    print(
        f"Source: {result.source.value}"
    )
    print(
        f"Jobs discovered: {len(result.jobs)}"
    )
    print(
        f"Job title: {discovered_job.title}"
    )
    print(
        f"Company: "
        f"{discovered_job.company_name}"
    )
    print(
        f"External ID: "
        f"{discovered_job.external_id}"
    )

    # --------------------------------------------------------------
    # 9. Validated URL navigation
    # --------------------------------------------------------------

    print()
    print("[9/10] Testing validated URL navigation...")

    job_url = (
        "https://www.linkedin.com/"
        "jobs/view/test-001"
    )

    adapter.open_url(
        session,
        job_url,
    )

    assert (
        session.current_url()
        == job_url
    )

    print("URL NAVIGATION successful")
    print(
        f"Current URL: {session.current_url()}"
    )

    # --------------------------------------------------------------
    # 10. Session helpers
    # --------------------------------------------------------------

    print()
    print("[10/10] Testing session helper methods...")

    session.click(
        "#test-button"
    )

    status = session.get_text(
        "#status"
    )

    assert (
        "#test-button"
        in session.clicked_selectors
    )

    assert status == "ready"

    print("SESSION HELPERS successful")
    print(
        "Click helper: successful"
    )
    print(
        f"Text helper result: {status}"
    )

    # --------------------------------------------------------------
    # Final
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("BASE JOB PORTAL ADAPTER INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
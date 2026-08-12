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
from src.shared.core.exceptions import ValidationError


# ----------------------------------------------------------------------
# Fake PortalSession
# ----------------------------------------------------------------------


class FakePortalSession:
    """
    Minimal in-memory PortalSession implementation.

    This test does not require Playwright because the purpose is to
    validate the BaseJobPortalAdapter independently.

    The implementation satisfies the complete PortalSession protocol
    defined by the domain layer.
    """

    def __init__(self) -> None:
        self._current_url = "about:blank"

        self._texts: dict[str, str] = {
            "#status": "ready",
        }

        self._text_lists: dict[str, list[str]] = {}

        self._attributes: dict[
            tuple[str, str],
            str | None,
        ] = {}

        self._attribute_lists: dict[
            tuple[str, str],
            list[str | None],
        ] = {}

        self._scoped_texts: dict[
            tuple[str, str, int],
            str,
        ] = {}

        self._scoped_attributes: dict[
            tuple[str, str, str, int],
            str | None,
        ] = {}

        self._element_counts: dict[str, int] = {}

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

    def get_texts(
        self,
        selector: str,
    ) -> list[str]:
        return list(
            self._text_lists.get(
                selector,
                [],
            )
        )

    def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> str | None:
        return self._attributes.get(
            (
                selector,
                attribute,
            )
        )

    def get_attributes(
        self,
        selector: str,
        attribute: str,
    ) -> list[str | None]:
        return list(
            self._attribute_lists.get(
                (
                    selector,
                    attribute,
                ),
                [],
            )
        )

    def get_scoped_text(
        self,
        parent_selector: str,
        child_selector: str,
        index: int,
    ) -> str:
        return self._scoped_texts.get(
            (
                parent_selector,
                child_selector,
                index,
            ),
            "",
        )

    def get_scoped_attribute(
        self,
        parent_selector: str,
        child_selector: str,
        attribute: str,
        index: int,
    ) -> str | None:
        return self._scoped_attributes.get(
            (
                parent_selector,
                child_selector,
                attribute,
                index,
            )
        )

    def get_element_count(
        self,
        selector: str,
    ) -> int:
        return self._element_counts.get(
            selector,
            0,
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
    print("On portal: True")

    # --------------------------------------------------------------
    # 5. Authentication
    # --------------------------------------------------------------

    print()
    print("[5/10] Testing portal authentication...")

    assert adapter.is_authenticated(
        session
    )

    print("AUTHENTICATION detection successful")
    print("Authenticated: True")

    # --------------------------------------------------------------
    # 6. Authentication flow
    # --------------------------------------------------------------

    print()
    print("[6/10] Testing authentication flow...")

    session._current_url = "about:blank"

    adapter.authenticate(
        session
    )

    assert (
        session.current_url()
        == "https://www.linkedin.com"
    )

    print("AUTHENTICATION flow successful")
    print(
        f"Current URL: {session.current_url()}"
    )

    # --------------------------------------------------------------
    # 7. Search criteria validation
    # --------------------------------------------------------------

    print()
    print("[7/10] Testing search criteria validation...")

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

    print("SEARCH CRITERIA validation successful")
    print(
        f"Keywords: {criteria.keywords}"
    )
    print(
        f"Locations: {criteria.locations}"
    )
    print(
        f"Maximum results: {criteria.maximum_results}"
    )

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

    assert (
        result.total_found
        == 1
    )

    assert (
        len(result.jobs)
        == 1
    )

    job = result.jobs[0]

    assert (
        job.external_id
        == "test-001"
    )

    assert (
        job.title
        == "Data Analyst"
    )

    assert (
        job.company_name
        == "Test Company"
    )

    assert (
        job.source
        == JobSourceType.LINKEDIN
    )

    print("JOB DISCOVERY successful")
    print(
        f"Jobs discovered: {len(result.jobs)}"
    )
    print(
        f"Job title: {job.title}"
    )
    print(
        f"Company: {job.company_name}"
    )

    # --------------------------------------------------------------
    # 9. Invalid session protection
    # --------------------------------------------------------------

    print()
    print("[9/10] Testing invalid session protection...")

    try:
        adapter.open_home(
            object()
        )

    except ValidationError as exc:
        print(
            "INVALID SESSION protection successful"
        )
        print(
            f"Expected error: {exc}"
        )

    else:
        raise AssertionError(
            "Expected invalid session protection "
            "to reject the session."
        )

    # --------------------------------------------------------------
    # 10. Invalid criteria protection
    # --------------------------------------------------------------

    print()
    print("[10/10] Testing invalid criteria protection...")

    invalid_criteria = JobSearchCriteria(
        keywords=(),
        locations=(),
        maximum_results=25,
    )

    try:
        adapter.discover_jobs(
            session,
            invalid_criteria,
        )

    except ValidationError as exc:
        print(
            "INVALID CRITERIA protection successful"
        )
        print(
            f"Expected error: {exc}"
        )

    else:
        raise AssertionError(
            "Expected invalid criteria protection "
            "to reject empty search criteria."
        )

    print()
    print("=" * 70)
    print("BASE JOB PORTAL ADAPTER TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
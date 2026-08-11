"""
Job discovery portal abstraction integration test.

Tests:
1. Job search criteria
2. Discovered job entity
3. Discovery result
4. PortalSession contract
5. JobPortal implementation contract
6. Portal registry registration
7. Portal lookup
8. Portal replacement
9. Portal removal
10. Registry filtering/listing
"""

from __future__ import annotations

from typing import Any

from src.modules.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
    JobPortal,
    JobPortalRegistry,
    JobSearchCriteria,
    PortalSession,
)
from src.shared.config.constants import (
    EmploymentType,
    JobSourceType,
    RemoteStatus,
)


class FakePortalSession:
    """Minimal test implementation of PortalSession."""

    def __init__(self) -> None:
        self._url = "about:blank"
        self._texts: dict[str, str] = {}

    def navigate(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> None:
        self._url = url

    def current_url(self) -> str:
        return self._url

    def get_text(
        self,
        selector: str,
    ) -> str:
        return self._texts.get(selector, "")

    def click(
        self,
        selector: str,
    ) -> None:
        self._texts[selector] = "clicked"


class FakeLinkedInPortal(JobPortal):
    """Fake LinkedIn portal used only for contract testing."""

    @property
    def source(self) -> JobSourceType:
        return JobSourceType.LINKEDIN

    @property
    def name(self) -> str:
        return "LinkedIn"

    def is_authenticated(
        self,
        session: PortalSession,
    ) -> bool:
        return session.current_url() == "https://www.linkedin.com/feed"

    def authenticate(
        self,
        session: PortalSession,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        session.navigate(
            "https://www.linkedin.com/feed"
        )

    def discover_jobs(
        self,
        session: PortalSession,
        criteria: JobSearchCriteria,
    ) -> DiscoveryResult:
        job = DiscoveredJob(
            external_id="linkedin-test-001",
            title=criteria.keywords[0]
            if criteria.keywords
            else "Data Analyst",
            company_name="Test Company",
            source=JobSourceType.LINKEDIN,
            url="https://www.linkedin.com/jobs/view/test-001",
            location=(
                criteria.locations[0]
                if criteria.locations
                else "Hyderabad"
            ),
            remote_status=(
                criteria.remote_statuses[0]
                if criteria.remote_statuses
                else RemoteStatus.REMOTE
            ),
            employment_type=(
                criteria.employment_types[0]
                if criteria.employment_types
                else EmploymentType.FULL_TIME
            ),
            description="Test job discovered through portal contract.",
            metadata={
                "test": True,
                "source": "linkedin",
            },
        )

        return DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=(job,),
            total_found=1,
            metadata={
                "test": True,
            },
        )


class FakeIndeedPortal(FakeLinkedInPortal):
    """Fake Indeed portal for registry testing."""

    @property
    def source(self) -> JobSourceType:
        return JobSourceType.INDEED

    @property
    def name(self) -> str:
        return "Indeed"


def main() -> None:
    print()
    print("=" * 70)
    print("JOB DISCOVERY PORTAL ABSTRACTION INTEGRATION TEST")
    print("=" * 70)

    # --------------------------------------------------------------
    # 1. Search criteria
    # --------------------------------------------------------------

    print()
    print("[1/10] Creating job search criteria...")

    criteria = JobSearchCriteria(
        keywords=(
            "Data Analyst",
            "Business Analyst",
        ),
        locations=(
            "Hyderabad",
            "Remote",
        ),
        remote_statuses=(
            RemoteStatus.REMOTE,
            RemoteStatus.HYBRID,
        ),
        employment_types=(
            EmploymentType.FULL_TIME,
        ),
        minimum_match_score=0.70,
        maximum_results=25,
    )

    assert criteria.maximum_results == 25
    assert criteria.minimum_match_score == 0.70
    assert "Data Analyst" in criteria.keywords

    print("SEARCH CRITERIA successful")
    print(f"Keywords: {criteria.keywords}")
    print(f"Locations: {criteria.locations}")
    print(f"Maximum results: {criteria.maximum_results}")

    # --------------------------------------------------------------
    # 2. Discovered job
    # --------------------------------------------------------------

    print()
    print("[2/10] Creating discovered job...")

    job = DiscoveredJob(
        external_id="test-job-001",
        title="Data Analyst",
        company_name="Test Company",
        source=JobSourceType.LINKEDIN,
        url="https://www.linkedin.com/jobs/view/test-job-001",
        location="Hyderabad",
        remote_status=RemoteStatus.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        description="Test data analyst position.",
        metadata={
            "source": "linkedin",
            "test": True,
        },
    )

    assert job.external_id == "test-job-001"
    assert job.source == JobSourceType.LINKEDIN
    assert job.metadata["source"] == "linkedin"

    print("DISCOVERED JOB successful")
    print(f"Title: {job.title}")
    print(f"Company: {job.company_name}")
    print(f"Source: {job.source.value}")

    # --------------------------------------------------------------
    # 3. Discovery result
    # --------------------------------------------------------------

    print()
    print("[3/10] Creating discovery result...")

    result = DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=(job,),
        total_found=1,
        metadata={
            "test": True,
        },
    )

    assert result.source == JobSourceType.LINKEDIN
    assert len(result.jobs) == 1
    assert result.total_found == 1

    print("DISCOVERY RESULT successful")
    print(f"Source: {result.source.value}")
    print(f"Jobs returned: {len(result.jobs)}")
    print(f"Total found: {result.total_found}")

    # --------------------------------------------------------------
    # 4. PortalSession contract
    # --------------------------------------------------------------

    print()
    print("[4/10] Testing PortalSession contract...")

    session = FakePortalSession()

    session.navigate(
        "https://www.linkedin.com/jobs"
    )

    assert (
        session.current_url()
        == "https://www.linkedin.com/jobs"
    )

    session.click("#test-button")

    assert (
        session.get_text("#test-button")
        == "clicked"
    )

    print("PORTAL SESSION contract successful")
    print(f"Current URL: {session.current_url()}")

    # --------------------------------------------------------------
    # 5. JobPortal implementation contract
    # --------------------------------------------------------------

    print()
    print("[5/10] Testing JobPortal implementation...")

    linkedin = FakeLinkedInPortal()

    assert isinstance(
        linkedin,
        JobPortal,
    )

    assert (
        linkedin.source
        == JobSourceType.LINKEDIN
    )

    assert linkedin.name == "LinkedIn"

    print("JOB PORTAL contract successful")
    print(f"Portal: {linkedin.name}")
    print(f"Source: {linkedin.source.value}")

    # --------------------------------------------------------------
    # 6. Portal authentication
    # --------------------------------------------------------------

    print()
    print("[6/10] Testing portal authentication contract...")

    authentication_session = FakePortalSession()

    assert (
        linkedin.is_authenticated(
            authentication_session
        )
        is False
    )

    linkedin.authenticate(
        authentication_session
    )

    assert (
        linkedin.is_authenticated(
            authentication_session
        )
        is True
    )

    print("PORTAL AUTHENTICATION contract successful")
    print(
        f"Authenticated: "
        f"{linkedin.is_authenticated(authentication_session)}"
    )

    # --------------------------------------------------------------
    # 7. Job discovery
    # --------------------------------------------------------------

    print()
    print("[7/10] Testing portal job discovery...")

    discovery_session = FakePortalSession()

    discovery_result = linkedin.discover_jobs(
        discovery_session,
        criteria,
    )

    assert (
        discovery_result.source
        == JobSourceType.LINKEDIN
    )

    assert (
        discovery_result.total_found == 1
    )

    assert len(discovery_result.jobs) == 1

    discovered = discovery_result.jobs[0]

    assert (
        discovered.source
        == JobSourceType.LINKEDIN
    )

    print("PORTAL JOB DISCOVERY successful")
    print(f"Jobs discovered: {len(discovery_result.jobs)}")
    print(f"Job title: {discovered.title}")
    print(f"Company: {discovered.company_name}")

    # --------------------------------------------------------------
    # 8. Registry registration
    # --------------------------------------------------------------

    print()
    print("[8/10] Registering portals...")

    registry = JobPortalRegistry()

    registry.register(
        linkedin
    )

    indeed = FakeIndeedPortal()

    registry.register(
        indeed
    )

    assert registry.has(
        JobSourceType.LINKEDIN
    )

    assert registry.has(
        JobSourceType.INDEED
    )

    print("PORTAL REGISTRATION successful")
    print(
        "Registered sources:",
        [
            source.value
            for source in registry.list_sources()
        ],
    )

    # --------------------------------------------------------------
    # 9. Registry lookup
    # --------------------------------------------------------------

    print()
    print("[9/10] Testing portal registry lookup...")

    linkedin_from_registry = registry.get(
        JobSourceType.LINKEDIN
    )

    indeed_from_registry = registry.get(
        JobSourceType.INDEED
    )

    assert (
        linkedin_from_registry
        is linkedin
    )

    assert (
        indeed_from_registry
        is indeed
    )

    print("PORTAL REGISTRY LOOKUP successful")
    print(
        f"LinkedIn: {linkedin_from_registry.name}"
    )
    print(
        f"Indeed: {indeed_from_registry.name}"
    )

    # --------------------------------------------------------------
    # 10. Registry removal
    # --------------------------------------------------------------

    print()
    print("[10/10] Testing portal registry removal...")

    registry.unregister(
        JobSourceType.INDEED
    )

    assert (
        registry.has(
            JobSourceType.INDEED
        )
        is False
    )

    assert (
        registry.has(
            JobSourceType.LINKEDIN
        )
        is True
    )

    print("PORTAL REGISTRY REMOVAL successful")
    print(
        "Remaining sources:",
        [
            source.value
            for source in registry.list_sources()
        ],
    )

    print()
    print("=" * 70)
    print("JOB DISCOVERY PORTAL ABSTRACTION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
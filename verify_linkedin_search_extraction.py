"""
Local LinkedIn search and extraction integration test.

This test does NOT connect to LinkedIn.

It verifies:

    1. Search URL generation.
    2. PortalSession compatibility.
    3. Job-card extraction.
    4. DiscoveredJob normalization.
    5. Maximum-result handling.
    6. DiscoveryResult creation.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.entities.job_discovery import (
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    PortalSession,
)
from src.modules.job_discovery.infrastructure.portals import (
    LinkedInPortalAdapter,
    LinkedInJobCardExtractor,
    LinkedInSearchBuilder,
)
from src.shared.config.constants import JobSourceType


class FakePortalSession:
    """
    Deterministic fake PortalSession for local testing.

    No network connection is performed.
    """

    def __init__(
        self,
        *,
        current_url: str = (
            "https://www.linkedin.com/jobs/search/"
        ),
    ) -> None:
        self._current_url = current_url

        self.navigated_urls: list[str] = []

        self.clicked_selectors: list[str] = []

        self.text_values: dict[
    str,
    list[str],
] = {
    "article[data-job-id] .job-title": [
        "Data Analyst",
        "Business Analyst",
        "Senior Data Analyst",
    ],
    "article[data-job-id] .job-company": [
        "Test Company",
        "Example Technologies",
        "Analytics Corp",
    ],
    "article[data-job-id] .job-location": [
        "Hyderabad, Telangana, India",
        "Remote",
        "Bengaluru, Karnataka, India",
    ],
}

        self.attribute_values: dict[
    tuple[str, str],
    list[str | None],
] = {
    (
        "article[data-job-id]",
        "data-job-id",
    ): [
        "linkedin-test-001",
        "linkedin-test-002",
        "linkedin-test-003",
    ],
    (
        "article[data-job-id] a.job-link",
        "href",
    ): [
        "/jobs/view/linkedin-test-001",
        "/jobs/view/linkedin-test-002",
        "/jobs/view/linkedin-test-003",
    ],
}

    # --------------------------------------------------------------
    # PortalSession
    # --------------------------------------------------------------

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
        values = self.get_texts(
            selector
        )

        if not values:
            return ""

        return values[0]

    def get_texts(
        self,
        selector: str,
    ) -> list[str]:
        return list(
            self.text_values.get(
                selector,
                [],
            )
        )

    def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> str | None:
        values = self.get_attributes(
            selector,
            attribute,
        )

        if not values:
            return None

        return values[0]

    def get_attributes(
        self,
        selector: str,
        attribute: str,
    ) -> list[str | None]:
        return list(
            self.attribute_values.get(
                (
                    selector,
                    attribute,
                ),
                [],
            )
        )

    def get_element_count(
        self,
        selector: str,
    ) -> int:
        if selector == "article[data-job-id]":
            return 3

        return len(
            self.text_values.get(selector, [])
        )

    def get_scoped_text(
        self,
        parent_selector: str,
        child_selector: str,
        index: int,
    ) -> str:
        if parent_selector != "article[data-job-id]":
            raise ValueError(
                f"Unexpected parent selector: {parent_selector}"
            )

        values = self.text_values.get(
            f"article[data-job-id] {child_selector}",
            [],
        )

        if index < 0 or index >= len(values):
            raise IndexError(
                f"Invalid job-card index: {index}"
            )

        return values[index]

    def get_scoped_attribute(
        self,
        parent_selector: str,
        child_selector: str,
        attribute: str,
        index: int,
    ) -> str | None:
        if parent_selector != "article[data-job-id]":
            raise ValueError(
                f"Unexpected parent selector: {parent_selector}"
            )

        key = (
            f"article[data-job-id] {child_selector}",
            attribute,
        )

        values = self.attribute_values.get(
            key,
            [],
        )

        if index < 0 or index >= len(values):
            raise IndexError(
                f"Invalid job-card index: {index}"
            )

        return values[index]

    def click(
        self,
        selector: str,
    ) -> None:
        self.clicked_selectors.append(
            selector
        )


def main() -> None:
    print()
    print("=" * 70)
    print("LINKEDIN SEARCH AND EXTRACTION INTEGRATION TEST")
    print("=" * 70)

    # ==============================================================
    # 1. Create search criteria
    # ==============================================================

    print()
    print("[1/10] Creating search criteria...")

    criteria = JobSearchCriteria(
        keywords=(
            "Data Analyst",
            "Business Analyst",
        ),
        locations=(
            "Hyderabad",
            "Remote",
        ),
        maximum_results=3,
    )

    print(
        "SEARCH CRITERIA successful"
    )

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

    # ==============================================================
    # 2. Test search builder
    # ==============================================================

    print()
    print("[2/10] Testing LinkedIn search URL builder...")

    builder = LinkedInSearchBuilder(
        base_url="https://www.linkedin.com"
    )

    urls = builder.build_urls(
        criteria
    )

    assert len(urls) == 2

    assert (
        "keywords=Data+Analyst+OR+Business+Analyst"
        in urls[0]
    )

    assert (
        "location=Hyderabad"
        in urls[0]
    )

    assert (
        "location=Remote"
        in urls[1]
    )

    print(
        "SEARCH URL BUILDER successful"
    )

    for url in urls:
        print(
            f"- {url}"
        )

    # ==============================================================
    # 3. Test single URL generation
    # ==============================================================

    print()
    print("[3/10] Testing single search URL generation...")

    single_url = builder.build_url(
        keywords="Data Analyst",
        location="Hyderabad",
    )

    assert (
        single_url
        == (
            "https://www.linkedin.com/jobs/search/"
            "?keywords=Data+Analyst"
            "&location=Hyderabad"
        )
    )

    print(
        "SINGLE SEARCH URL successful"
    )

    print(
        f"URL: {single_url}"
    )

    # ==============================================================
    # 4. Create fake PortalSession
    # ==============================================================

    print()
    print("[4/10] Creating local PortalSession...")

    session = FakePortalSession()

    assert isinstance(
        session,
        PortalSession,
    )

    print(
        "PORTAL SESSION successful"
    )

    print(
        "Implements PortalSession: True"
    )

    # ==============================================================
    # 5. Create extractor
    # ==============================================================

    print()
    print("[5/10] Creating job-card extractor...")

    extractor = LinkedInJobCardExtractor()

    assert isinstance(
        extractor,
        LinkedInJobCardExtractor,
    )

    print(
        "JOB EXTRACTOR creation successful"
    )

    print(
        f"Card selector: "
        f"{extractor.card_selector}"
    )

    # ==============================================================
    # 6. Extract jobs
    # ==============================================================

    print()
    print("[6/10] Extracting local job cards...")

    jobs = extractor.extract(
        session,
        maximum_results=3,
    )

    assert len(jobs) == 3

    print(
        "JOB EXTRACTION successful"
    )

    print(
        f"Jobs extracted: {len(jobs)}"
    )

    for job in jobs:
        print(
            f"- {job.title} | "
            f"{job.company_name} | "
            f"{job.location}"
        )

    # ==============================================================
    # 7. Verify first normalized job
    # ==============================================================

    print()
    print("[7/10] Verifying normalized DiscoveredJob...")

    first_job = jobs[0]

    assert (
        first_job.external_id
        == "linkedin-test-001"
    )

    assert (
        first_job.title
        == "Data Analyst"
    )

    assert (
        first_job.company_name
        == "Test Company"
    )

    assert (
        first_job.source
        == JobSourceType.LINKEDIN
    )

    assert (
        first_job.url
        == (
            "https://www.linkedin.com"
            "/jobs/view/linkedin-test-001"
        )
    )

    assert (
        first_job.location
        == "Hyderabad, Telangana, India"
    )

    print(
        "NORMALIZATION successful"
    )

    print(
        f"External ID: {first_job.external_id}"
    )

    print(
        f"Title: {first_job.title}"
    )

    print(
        f"Company: {first_job.company_name}"
    )

    print(
        f"Source: {first_job.source.value}"
    )

    print(
        f"URL: {first_job.url}"
    )

    # ==============================================================
    # 8. Test maximum results
    # ==============================================================

    print()
    print("[8/10] Testing maximum-result handling...")

    limited_jobs = extractor.extract(
        session,
        maximum_results=2,
    )

    assert len(limited_jobs) == 2

    assert (
        limited_jobs[0].external_id
        == "linkedin-test-001"
    )

    assert (
        limited_jobs[1].external_id
        == "linkedin-test-002"
    )

    print(
        "MAXIMUM RESULT handling successful"
    )

    print(
        f"Requested: 2"
    )

    print(
        f"Returned: {len(limited_jobs)}"
    )

    # ==============================================================
    # 9. Test adapter integration
    # ==============================================================

    print()
    print("[9/10] Testing LinkedIn adapter integration...")

    adapter = LinkedInPortalAdapter(
        base_url="https://www.linkedin.com"
    )

    result = adapter.discover_jobs(
        session,
        criteria,
    )

    assert (
        result.source
        == JobSourceType.LINKEDIN
    )

    assert len(result.jobs) == 3

    assert (
        result.total_found
        == 3
    )

    assert (
        result.jobs[0].title
        == "Data Analyst"
    )

    assert (
        result.jobs[1].title
        == "Business Analyst"
    )

    assert (
        result.jobs[2].title
        == "Senior Data Analyst"
    )

    print(
        "ADAPTER INTEGRATION successful"
    )

    print(
        f"Source: {result.source.value}"
    )

    print(
        f"Jobs returned: {len(result.jobs)}"
    )

    print(
        f"Total found: {result.total_found}"
    )

    # ==============================================================
    # 10. Test search navigation
    # ==============================================================

    print()
    print("[10/10] Testing search navigation...")

    search_urls = adapter.build_search_urls(
        criteria
    )

    adapter.open_url(
        session,
        search_urls[0],
    )

    assert (
        session.current_url()
        == search_urls[0]
    )

    assert (
        session.navigated_urls[-1]
        == search_urls[0]
    )

    print(
        "SEARCH NAVIGATION successful"
    )

    print(
        f"Current URL: {session.current_url()}"
    )

    # ==============================================================
    # Final
    # ==============================================================

    print()
    print("=" * 70)
    print(
        "LINKEDIN SEARCH AND EXTRACTION INTEGRATION TEST PASSED"
    )
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
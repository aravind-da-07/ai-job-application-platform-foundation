"""
LinkedIn portal adapter integration test.

This test validates the LinkedIn adapter against the domain contracts
without connecting to the real LinkedIn website.

The fake PortalSession implements the complete PortalSession contract
and provides the deterministic local LinkedIn job-card DOM expected by
LinkedInJobCardExtractor.
"""

from __future__ import annotations

from typing import Any

from src.modules.job_discovery.domain.entities.job_discovery import (
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    PortalSession,
)
from src.modules.job_discovery.infrastructure.portals import (
    LinkedInPortalAdapter,
)
from src.shared.config.constants import JobSourceType


# ============================================================================
# Fake PortalSession
# ============================================================================


class FakePortalSession:
    """
    Deterministic in-memory PortalSession used by the integration test.

    No browser or real LinkedIn connection is required.

    The session implements the complete PortalSession contract and exposes
    the local LinkedIn test DOM expected by LinkedInJobCardExtractor:

        article[data-job-id]
        article[data-job-id] .job-title
        article[data-job-id] .job-company
        article[data-job-id] .job-location
        article[data-job-id] a.job-link
    """

    def __init__(
        self,
        initial_url: str = "about:blank",
    ) -> None:

        self._current_url = initial_url

        self.clicked_selectors: list[str] = []
        self.navigated_urls: list[str] = []

        # ------------------------------------------------------------------
        # Page-level text values
        # ------------------------------------------------------------------

        self._texts: dict[str, list[str]] = {
            "#status": ["ready"],
        }

        # ------------------------------------------------------------------
        # Page-level attributes
        # ------------------------------------------------------------------

        self._attributes: dict[
            tuple[str, str],
            list[str | None],
        ] = {}

        # ------------------------------------------------------------------
        # Deterministic local LinkedIn test DOM
        #
        # This is exactly what LinkedInJobCardExtractor expects.
        # ------------------------------------------------------------------

        self._attributes[
            (
                "article[data-job-id]",
                "data-job-id",
            )
        ] = [
            "test-001",
        ]

        self._texts[
            "article[data-job-id] .job-title"
        ] = [
            "Data Analyst",
        ]

        self._texts[
            "article[data-job-id] .job-company"
        ] = [
            "Test Company",
        ]

        self._texts[
            "article[data-job-id] .job-location"
        ] = [
            "Hyderabad",
        ]

        self._attributes[
            (
                "article[data-job-id] a.job-link",
                "href",
            )
        ] = [
            "/jobs/view/test-001",
        ]

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> None:
        """
        Simulate browser navigation.
        """

        self._current_url = url

        self.navigated_urls.append(url)

    def current_url(self) -> str:
        """
        Return the simulated current URL.
        """

        return self._current_url

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    def get_text(
        self,
        selector: str,
    ) -> str:
        """
        Return text from the first matching simulated element.
        """

        values = self._texts.get(
            selector,
            [],
        )

        if not values:
            return ""

        return values[0]

    def get_texts(
        self,
        selector: str,
    ) -> list[str]:
        """
        Return text from all matching simulated elements.
        """

        return list(
            self._texts.get(
                selector,
                [],
            )
        )

    # ------------------------------------------------------------------
    # Attribute helpers
    # ------------------------------------------------------------------

    def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> str | None:
        """
        Return an attribute from the first matching simulated element.
        """

        values = self._attributes.get(
            (
                selector,
                attribute,
            ),
            [],
        )

        if not values:
            return None

        return values[0]

    def get_attributes(
        self,
        selector: str,
        attribute: str,
    ) -> list[str | None]:
        """
        Return attributes from all matching simulated elements.
        """

        return list(
            self._attributes.get(
                (
                    selector,
                    attribute,
                ),
                [],
            )
        )

    # ------------------------------------------------------------------
    # Scoped element helpers
    # ------------------------------------------------------------------

    def get_scoped_text(
        self,
        parent_selector: str,
        child_selector: str,
        index: int,
    ) -> str:
        """
        Return text from a child inside a simulated parent.

        The current LinkedIn local extractor does not require this method,
        but PortalSession requires it, so it is implemented for contract
        compatibility.
        """

        selector = (
            f"{parent_selector} "
            f"{child_selector}"
        )

        values = self.get_texts(
            selector
        )

        if index < 0 or index >= len(values):
            return ""

        return values[index]

    def get_scoped_attribute(
        self,
        parent_selector: str,
        child_selector: str,
        attribute: str,
        index: int,
    ) -> str | None:
        """
        Return an attribute from a child inside a simulated parent.
        """

        selector = (
            f"{parent_selector} "
            f"{child_selector}"
        )

        values = self.get_attributes(
            selector,
            attribute,
        )

        if index < 0 or index >= len(values):
            return None

        return values[index]

    # ------------------------------------------------------------------
    # Element helpers
    # ------------------------------------------------------------------

    def get_element_count(
        self,
        selector: str,
    ) -> int:
        """
        Return the number of simulated matching elements.
        """

        if selector == "article[data-job-id]":
            return 1

        text_values = self._texts.get(
            selector
        )

        if text_values is not None:
            return len(text_values)

        attribute_values = self._attributes.get(
            (
                selector,
                "href",
            )
        )

        if attribute_values is not None:
            return len(attribute_values)

        return 0

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def click(
        self,
        selector: str,
    ) -> None:
        """
        Record a simulated click.
        """

        self.clicked_selectors.append(
            selector
        )


# ============================================================================
# Main integration test
# ============================================================================


def main() -> None:

    print()
    print("=" * 70)
    print("LINKEDIN PORTAL ADAPTER INTEGRATION TEST")
    print("=" * 70)

    # ======================================================================
    # 1. Create LinkedIn adapter
    # ======================================================================

    print()
    print("[1/10] Creating LinkedIn adapter...")

    adapter = LinkedInPortalAdapter(
        base_url="https://www.linkedin.com"
    )

    assert (
        adapter.name
        == "LinkedIn"
    )

    assert (
        adapter.source
        == JobSourceType.LINKEDIN
    )

    assert (
        adapter.base_url
        == "https://www.linkedin.com"
    )

    print(
        "LINKEDIN ADAPTER creation successful"
    )

    print(
        f"Name: {adapter.name}"
    )

    print(
        f"Source: {adapter.source.value}"
    )

    print(
        f"Base URL: {adapter.base_url}"
    )

    # ======================================================================
    # 2. Create PortalSession
    # ======================================================================

    print()
    print("[2/10] Creating PortalSession...")

    session = FakePortalSession()

    assert isinstance(
        session,
        PortalSession,
    )

    print(
        "PORTAL SESSION creation successful"
    )

    print(
        "Implements PortalSession: True"
    )

    # ======================================================================
    # 3. Home navigation
    # ======================================================================

    print()
    print("[3/10] Testing LinkedIn home navigation...")

    adapter.open_home(
        session
    )

    assert (
        session.current_url()
        == "https://www.linkedin.com"
    )

    print(
        "HOME NAVIGATION successful"
    )

    print(
        f"Current URL: {session.current_url()}"
    )

    # ======================================================================
    # 4. Portal detection
    # ======================================================================

    print()
    print("[4/10] Testing LinkedIn portal detection...")

    assert adapter.is_on_portal(
        session
    )

    print(
        "PORTAL DETECTION successful"
    )

    print(
        "On LinkedIn: True"
    )

    # ======================================================================
    # 5. Authentication detection
    # ======================================================================

    print()
    print("[5/10] Testing authentication detection...")

    authenticated = adapter.is_authenticated(
        session
    )

    assert authenticated is True

    print(
        "AUTHENTICATION detection successful"
    )

    print(
        f"Authenticated: {authenticated}"
    )

    # ======================================================================
    # 6. Authentication flow
    # ======================================================================

    print()
    print("[6/10] Testing authentication flow...")

    adapter.authenticate(
        session
    )

    assert (
        session.current_url()
        == "https://www.linkedin.com"
    )

    print(
        "AUTHENTICATION flow successful"
    )

    print(
        f"Current URL: {session.current_url()}"
    )

    # ======================================================================
    # 7. Search criteria
    # ======================================================================

    print()
    print("[7/10] Testing LinkedIn search criteria...")

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

    urls = adapter.build_search_urls(
        criteria
    )

    assert len(urls) == 2

    assert (
        "Data+Analyst"
        in urls[0]
        or "Data%20Analyst"
        in urls[0]
    )

    print(
        "SEARCH CRITERIA validation successful"
    )

    print(
        f"Keywords: {criteria.keywords}"
    )

    print(
        f"Locations: {criteria.locations}"
    )

    print(
        f"Maximum results: {criteria.maximum_results}"
    )

    # ======================================================================
    # 8. LinkedIn job discovery
    # ======================================================================

    print()
    print("[8/10] Testing LinkedIn job discovery...")

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
        job.location
        == "Hyderabad"
    )

    assert (
        job.source
        == JobSourceType.LINKEDIN
    )

    assert (
        job.url
        == "https://www.linkedin.com/jobs/view/test-001"
    )

    print(
        "JOB DISCOVERY successful"
    )

    print(
        f"Jobs discovered: {result.total_found}"
    )

    print(
        f"Job title: {job.title}"
    )

    print(
        f"Company: {job.company_name}"
    )

    print(
        f"Location: {job.location}"
    )

    print(
        f"External ID: {job.external_id}"
    )

    print(
        f"URL: {job.url}"
    )

    # ======================================================================
    # 9. Search URL generation
    # ======================================================================

    print()
    print("[9/10] Testing LinkedIn search URL generation...")

    search_urls = adapter.build_search_urls(
        criteria
    )

    assert (
        len(search_urls)
        == 2
    )

    assert all(
        url.startswith(
            "https://www.linkedin.com/jobs/search/"
        )
        for url in search_urls
    )

    assert all(
        "keywords="
        in url
        for url in search_urls
    )

    assert all(
        "location="
        in url
        for url in search_urls
    )

    print(
        "SEARCH URL generation successful"
    )

    for index, url in enumerate(
        search_urls,
        start=1,
    ):
        print(
            f"Search URL {index}: {url}"
        )

    # ======================================================================
    # 10. Invalid criteria protection
    # ======================================================================

    print()
    print("[10/10] Testing invalid criteria protection...")

    invalid_criteria = JobSearchCriteria(
        keywords=(),
        locations=(
            "Hyderabad",
        ),
        maximum_results=25,
    )

    try:

        adapter.discover_jobs(
            session,
            invalid_criteria,
        )

    except Exception as exc:

        print(
            "INVALID CRITERIA protection successful"
        )

        print(
            f"Expected error: {exc}"
        )

    else:

        raise AssertionError(
            "Invalid criteria was not rejected."
        )

    # ======================================================================
    # Final result
    # ======================================================================

    print()
    print("=" * 70)
    print(
        "LINKEDIN PORTAL ADAPTER INTEGRATION TEST PASSED"
    )
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
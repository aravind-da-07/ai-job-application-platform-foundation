"""
LinkedIn portal adapter integration test.

This test validates the LinkedIn adapter against the domain contracts
without connecting to the real LinkedIn website.
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
)
from src.shared.config.constants import JobSourceType


class FakePortalSession:
    """
    Minimal in-memory PortalSession implementation.

    This fake session implements the complete PortalSession contract,
    including the element-reading methods required by the current
    browser abstraction.
    """

    def __init__(
        self,
        initial_url: str = "about:blank",
    ) -> None:
        self._current_url = initial_url

        self.clicked_selectors: list[str] = []

        self.navigated_urls: list[str] = []

        self._texts: dict[str, str] = {
            "#status": "ready",
        }

        self._attributes: dict[
            tuple[str, str],
            str,
        ] = {
            (
                "#job-link",
                "href",
            ): "/jobs/view/test-001",
        }

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

        self.navigated_urls.append(
            url
        )

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
        Return text from the first simulated element.
        """

        return self._texts.get(
            selector,
            "",
        )

    def get_texts(
        self,
        selector: str,
    ) -> list[str]:
        """
        Return text from all simulated matching elements.
        """

        value = self._texts.get(
            selector
        )

        if value is None:
            return []

        return [value]

    # ------------------------------------------------------------------
    # Attribute helpers
    # ------------------------------------------------------------------

    def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> str | None:
        """
        Return an attribute from the first simulated element.
        """

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
        """
        Return attributes from all simulated matching elements.
        """

        value = self._attributes.get(
            (
                selector,
                attribute,
            )
        )

        if value is None:
            return []

        return [value]

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


def main() -> None:
    print()
    print("=" * 70)
    print("LINKEDIN PORTAL ADAPTER INTEGRATION TEST")
    print("=" * 70)

    # ==============================================================
    # 1. Create adapter
    # ==============================================================

    print()
    print("[1/10] Creating LinkedIn adapter...")

    adapter = LinkedInPortalAdapter(
        base_url="https://www.linkedin.com"
    )

    assert adapter.name == "LinkedIn"

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

    # ==============================================================
    # 2. Create PortalSession
    # ==============================================================

    print()
    print("[2/10] Creating PortalSession...")

    session = FakePortalSession(
        initial_url="about:blank"
    )

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

    # ==============================================================
    # 3. Test LinkedIn home navigation
    # ==============================================================

    print()
    print(
        "[3/10] Testing LinkedIn home navigation..."
    )

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

    # ==============================================================
    # 4. Test portal detection
    # ==============================================================

    print()
    print(
        "[4/10] Testing LinkedIn portal detection..."
    )

    assert adapter.is_on_portal(
        session
    )

    print(
        "PORTAL DETECTION successful"
    )

    print(
        "Current session belongs to LinkedIn: True"
    )

    # ==============================================================
    # 5. Test authentication detection
    # ==============================================================

    print()
    print(
        "[5/10] Testing authentication detection..."
    )

    authenticated = adapter.is_authenticated(
        session
    )

    assert authenticated is True

    print(
        "AUTHENTICATION DETECTION successful"
    )

    print(
        f"Authenticated: {authenticated}"
    )

    # ==============================================================
    # 6. Test authentication page detection
    # ==============================================================

    print()
    print(
        "[6/10] Testing authentication-page detection..."
    )

    login_session = FakePortalSession(
        initial_url=(
            "https://www.linkedin.com/login"
        )
    )

    login_authenticated = (
        adapter.is_authenticated(
            login_session
        )
    )

    assert login_authenticated is False

    print(
        "AUTHENTICATION PAGE DETECTION successful"
    )

    print(
        "Login page detected as authenticated: False"
    )

    # ==============================================================
    # 7. Test search criteria
    # ==============================================================

    print()
    print(
        "[7/10] Testing LinkedIn search criteria..."
    )

    criteria = JobSearchCriteria(
        keywords=(
            "Data Analyst",
            "Business Analyst",
        ),
        locations=(
            "Hyderabad",
            "Remote",
        ),
        maximum_results=10,
    )

    adapter._validate_criteria(
        criteria
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
    # 8. Test job discovery contract
    # ==============================================================

    print()
    print(
        "[8/10] Testing LinkedIn job discovery contract..."
    )

    result = adapter.discover_jobs(
        session,
        criteria,
    )

    assert (
        result.source
        == JobSourceType.LINKEDIN
    )

    assert result.jobs == ()

    assert result.total_found == 0

    assert (
        result.metadata["portal"]
        == "LinkedIn"
    )

    assert (
        result.metadata["source"]
        == "linkedin"
    )

    assert (
        result.metadata["search_keywords"]
        == [
            "Data Analyst",
            "Business Analyst",
        ]
    )

    assert (
        result.metadata["search_locations"]
        == [
            "Hyderabad",
            "Remote",
        ]
    )

    print(
        "JOB DISCOVERY CONTRACT successful"
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
    # 9. Test jobs navigation and attributes
    # ==============================================================

    print()
    print(
        "[9/10] Testing LinkedIn jobs navigation and attributes..."
    )

    adapter.open_url(
        session,
        adapter.JOBS_URL,
    )

    assert (
        session.current_url()
        == "https://www.linkedin.com/jobs"
    )

    href = session.get_attribute(
        "#job-link",
        "href",
    )

    assert (
        href
        == "/jobs/view/test-001"
    )

    hrefs = session.get_attributes(
        "#job-link",
        "href",
    )

    assert hrefs == [
        "/jobs/view/test-001"
    ]

    print(
        "JOBS NAVIGATION successful"
    )

    print(
        f"Current URL: {session.current_url()}"
    )

    print(
        "ATTRIBUTE HELPERS successful"
    )

    print(
        f"Job href: {href}"
    )

    # ==============================================================
    # 10. Test PortalSession helpers
    # ==============================================================

    print()
    print(
        "[10/10] Testing PortalSession helpers..."
    )

    session.click(
        "#test-button"
    )

    status = session.get_text(
        "#status"
    )

    statuses = session.get_texts(
        "#status"
    )

    assert (
        "#test-button"
        in session.clicked_selectors
    )

    assert status == "ready"

    assert statuses == [
        "ready"
    ]

    print(
        "SESSION HELPERS successful"
    )

    print(
        "Click: successful"
    )

    print(
        f"Text: {status}"
    )

    print(
        f"Texts: {statuses}"
    )

    # ==============================================================
    # Final
    # ==============================================================

    print()
    print("=" * 70)
    print(
        "LINKEDIN PORTAL ADAPTER INTEGRATION TEST PASSED"
    )
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
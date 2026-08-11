"""
LinkedIn job portal adapter.

This adapter contains LinkedIn-specific navigation and discovery
behavior while keeping the domain layer independent from Playwright.
"""

from __future__ import annotations

from typing import Any

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveryResult,
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    PortalSession,
)
from src.modules.job_discovery.infrastructure.portals.base_portal_adapter import (
    BaseJobPortalAdapter,
)
from src.modules.job_discovery.infrastructure.portals.linkedin.linkedin_search import (
    LinkedInJobCardExtractor,
    LinkedInSearchBuilder,
)
from src.shared.config.constants import JobSourceType
from src.shared.core.exceptions import (
    AuthenticationRequiredError,
)


class LinkedInPortalAdapter(BaseJobPortalAdapter):
    """
    Concrete LinkedIn job portal adapter.

    Responsibilities:

        - Identify LinkedIn sessions.
        - Navigate to LinkedIn jobs.
        - Build search URLs.
        - Validate authentication.
        - Extract normalized jobs.
    """

    JOBS_URL = "https://www.linkedin.com/jobs"

    def __init__(
        self,
        *,
        base_url: str = "https://www.linkedin.com",
    ) -> None:
        super().__init__(
            base_url=base_url
        )

        self.search_builder = LinkedInSearchBuilder(
            base_url=self.base_url
        )

        self.job_extractor = LinkedInJobCardExtractor()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def source(self) -> JobSourceType:
        """Return the LinkedIn job source."""

        return JobSourceType.LINKEDIN

    @property
    def name(self) -> str:
        """Return the human-readable portal name."""

        return "LinkedIn"

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def is_authenticated(
        self,
        session: PortalSession,
    ) -> bool:
        """
        Determine whether the current LinkedIn session appears
        authenticated.

        This method does not bypass login, MFA, CAPTCHA, or any
        security control.
        """

        self._validate_session(
            session
        )

        current_url = (
            session.current_url()
            .strip()
            .lower()
        )

        if not current_url:
            return False

        authentication_paths = (
            "/login",
            "/signup",
            "/checkpoint",
            "/authwall",
        )

        if any(
            path in current_url
            for path in authentication_paths
        ):
            return False

        return self.is_on_portal(
            session
        )

    def authenticate(
        self,
        session: PortalSession,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Verify LinkedIn authentication state.

        Credentials are intentionally not accepted here.

        Interactive authentication, MFA, and CAPTCHA remain under
        explicit user control.
        """

        self._validate_session(
            session
        )

        self.open_home(
            session
        )

        if not self.is_authenticated(
            session
        ):
            raise AuthenticationRequiredError(
                "LinkedIn authentication is required."
            )

    # ------------------------------------------------------------------
    # Search URL
    # ------------------------------------------------------------------

    def build_search_urls(
        self,
        criteria: JobSearchCriteria,
    ) -> tuple[str, ...]:
        """
        Build LinkedIn search URLs from domain criteria.
        """

        self._validate_criteria(
            criteria
        )

        return self.search_builder.build_urls(
            criteria
        )

    # ------------------------------------------------------------------
    # Job discovery
    # ------------------------------------------------------------------

    def discover_jobs(
        self,
        session: PortalSession,
        criteria: JobSearchCriteria,
    ) -> DiscoveryResult:
        """
        Discover and normalize jobs from the current LinkedIn
        search page.

        The method currently expects the session to already be on
        a LinkedIn jobs search page.

        Search navigation is kept separate so that URL generation
        and extraction can be tested independently.
        """

        self._validate_session(
            session
        )

        self._validate_criteria(
            criteria
        )

        jobs = self.job_extractor.extract(
            session,
            maximum_results=criteria.maximum_results,
        )

        return DiscoveryResult(
            source=self.source,
            jobs=jobs,
            total_found=len(jobs),
            metadata={
                "portal": self.name,
                "source": self.source.value,
                "search_keywords": list(
                    criteria.keywords
                ),
                "search_locations": list(
                    criteria.locations
                ),
            },
        )

    def discover_from_search_url(
        self,
        session: PortalSession,
        criteria: JobSearchCriteria,
    ) -> DiscoveryResult:
        """
        Navigate to the first generated LinkedIn search URL and
        extract jobs from the resulting page.

        This method will be connected to the real Playwright session
        only after local extraction tests pass.
        """

        self._validate_session(
            session
        )

        self._validate_criteria(
            criteria
        )

        search_urls = self.build_search_urls(
            criteria
        )

        if not search_urls:
            return DiscoveryResult(
                source=self.source,
                jobs=(),
                total_found=0,
                metadata={
                    "portal": self.name,
                    "source": self.source.value,
                },
            )

        self.open_url(
            session,
            search_urls[0],
        )

        return self.discover_jobs(
            session,
            criteria,
        )
"""
End-to-end local job discovery pipeline test.

This test uses the real:

    - BrowserEngine
    - PlaywrightPortalSession
    - LinkedInPortalAdapter
    - LinkedInJobCardExtractor
    - JobDiscoveryService
    - JobPortalRegistry

It intentionally does NOT use:

    - real LinkedIn
    - PostgreSQL
    - Supabase
    - real LinkedIn authentication

A local HTML page is used to simulate LinkedIn job results.

Pipeline under test:

    Local LinkedIn HTML
            |
            v
    Chromium / Playwright
            |
            v
    PlaywrightPortalSession
            |
            v
    LinkedInPortalAdapter
            |
            v
    LinkedInJobCardExtractor
            |
            v
    DiscoveryResult
            |
            v
    JobDiscoveryService
            |
            v
    InMemoryJobRepository
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.repositories.job.job_repository import (
    JobRepository,
)
from src.modules.job_discovery.infrastructure.browser.playwright_portal_session import (
    PlaywrightPortalSession,
)
from src.modules.job_discovery.infrastructure.portals.linkedin.linkedin_portal import (
    LinkedInPortalAdapter,
)
from src.modules.job_discovery.services.discovery.job_discovery_orchestrator import (
    JobDiscoveryOrchestrationResult,
    JobDiscoveryOrchestrator,
)
from src.modules.job_discovery.services.discovery.job_discovery_service import (
    JobDiscoveryService,
)
from src.modules.job_discovery.services.portal_registry import (
    JobPortalRegistry,
)
from src.shared.browser.browser_engine import BrowserEngine
from src.shared.config.constants import JobSourceType


class InMemoryJobRepository(JobRepository):
    """
    In-memory JobRepository implementation for integration testing.

    This implements the repository contract without requiring
    PostgreSQL, SQLAlchemy, or Supabase.
    """

    def __init__(self) -> None:
        self._jobs: dict[UUID, DiscoveredJob] = {}

        self._ids_by_external: dict[
            tuple[JobSourceType, str],
            UUID,
        ] = {}

    def create(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """
        Create a new discovered job.
        """

        key = (
            job.source,
            job.external_id,
        )

        if key in self._ids_by_external:
            raise ValueError(
                "Job already exists for this source and external job ID."
            )

        job_id = uuid4()

        self._jobs[job_id] = job
        self._ids_by_external[key] = job_id

        return job

    def get_by_id(
        self,
        job_id: UUID,
    ) -> DiscoveredJob | None:
        """
        Retrieve a job by its internal ID.
        """

        return self._jobs.get(
            job_id
        )

    def get_by_external_id(
        self,
        *,
        source: JobSourceType,
        external_job_id: str,
    ) -> DiscoveredJob | None:
        """
        Retrieve a job using source + external job ID.
        """

        key = (
            source,
            external_job_id,
        )

        job_id = self._ids_by_external.get(
            key
        )

        if job_id is None:
            return None

        return self._jobs.get(
            job_id
        )

    def upsert(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """
        Create or update a discovered job.
        """

        key = (
            job.source,
            job.external_id,
        )

        existing_id = self._ids_by_external.get(
            key
        )

        if existing_id is None:
            job_id = uuid4()

            self._jobs[job_id] = job
            self._ids_by_external[key] = job_id

            return job

        self._jobs[existing_id] = job

        return job

    def update(
        self,
        job_id: UUID,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """
        Update an existing job.
        """

        if job_id not in self._jobs:
            raise ValueError(
                f"Job with id {job_id} was not found."
            )

        self._jobs[job_id] = job

        self._ids_by_external[
            (
                job.source,
                job.external_id,
            )
        ] = job_id

        return job

    def list_active(
        self,
        *,
        source: JobSourceType | None = None,
        limit: int = 100,
    ) -> list[DiscoveredJob]:
        """
        Return active jobs.
        """

        if limit < 1:
            raise ValueError(
                "limit must be greater than zero."
            )

        jobs = list(
            self._jobs.values()
        )

        if source is not None:
            jobs = [
                job
                for job in jobs
                if job.source == source
            ]

        return jobs[:limit]

    def deactivate(
        self,
        job_id: UUID,
    ) -> None:
        """
        Remove a job from the active in-memory collection.
        """

        if job_id not in self._jobs:
            raise ValueError(
                f"Job with id {job_id} was not found."
            )

        del self._jobs[job_id]

    def count_active(
        self,
        *,
        source: JobSourceType | None = None,
    ) -> int:
        """
        Count active jobs.
        """

        if source is None:
            return len(
                self._jobs
            )

        return sum(
            1
            for job in self._jobs.values()
            if job.source == source
        )


def _write_linkedin_fixture(
    tmp_path: Path,
) -> Path:
    """
    Create a deterministic local LinkedIn-style jobs page.

    The selectors intentionally match the selectors supported by
    LinkedInJobCardExtractor.
    """

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>LinkedIn Jobs Test</title>
    </head>

    <body>

        <ul class="jobs-search__results-list">

            <li>
                <div
                    class="base-card"
                    data-entity-urn="urn:li:jobPosting:100001"
                >

                    <a
                        class="base-card__full-link"
                        href="https://www.linkedin.com/jobs/view/100001/"
                    >
                        View job
                    </a>

                    <h3 class="base-search-card__title">
                        Senior Data Analyst
                    </h3>

                    <h4 class="base-search-card__subtitle">
                        Example Analytics Ltd
                    </h4>

                    <span class="job-search-card__location">
                        Hyderabad, Telangana, India
                    </span>

                </div>
            </li>

            <li>
                <div
                    class="base-card"
                    data-entity-urn="urn:li:jobPosting:100002"
                >

                    <a
                        class="base-card__full-link"
                        href="https://www.linkedin.com/jobs/view/100002/"
                    >
                        View job
                    </a>

                    <h3 class="base-search-card__title">
                        Business Data Analyst
                    </h3>

                    <h4 class="base-search-card__subtitle">
                        Data Solutions Pvt Ltd
                    </h4>

                    <span class="job-search-card__location">
                        Hyderabad, Telangana, India
                    </span>

                </div>
            </li>

        </ul>

    </body>
    </html>
    """

    html_file = (
        tmp_path
        / "linkedin_jobs.html"
    )

    html_file.write_text(
        html,
        encoding="utf-8",
    )

    return html_file


class LocalLinkedInPortalAdapter(
    LinkedInPortalAdapter
):
    """
    LinkedIn adapter variant used only by this integration test.

    It reuses the real LinkedIn discovery and extraction logic but
    skips real LinkedIn authentication and navigation.
    """

    def authenticate(
        self,
        session,
        *,
        metadata=None,
    ) -> None:
        """
        Local test fixture does not require real authentication.
        """

        return None

    def discover_from_search_url(
        self,
        session,
        criteria,
    ):
        """
        Extract from the already-loaded local fixture.

        This bypasses real LinkedIn navigation while retaining the
        actual LinkedIn discovery/extraction implementation.
        """

        return self.discover_jobs(
            session,
            criteria,
        )


class LocalDiscoveryOrchestrator(
    JobDiscoveryOrchestrator
):
    """
    Test-only orchestrator that reuses an already-created
    Playwright session.

    The production orchestrator owns its browser lifecycle.

    This test variant keeps the browser/session open so the local
    HTML fixture can be used directly.
    """

    def __init__(
        self,
        *,
        portal_registry: JobPortalRegistry,
        discovery_service: JobDiscoveryService,
        session: PlaywrightPortalSession,
    ) -> None:
        super().__init__(
            portal_registry=portal_registry,
            discovery_service=discovery_service,
            browser_engine=None,
        )

        self._test_session = session

    def discover(
        self,
        *,
        source,
        criteria: JobSearchCriteria,
        storage_state=None,
    ) -> JobDiscoveryOrchestrationResult:
        """
        Execute discovery using the already-open test session.
        """

        if criteria is None:
            raise ValueError(
                "criteria cannot be None."
            )

        portal = self._portal_registry.get(
            source
        )

        portal.authenticate(
            self._test_session
        )

        discovery_result = portal.discover_jobs(
            self._test_session,
            criteria,
        )

        processing_result = (
            self._discovery_service.process(
                discovery_result
            )
        )

        return JobDiscoveryOrchestrationResult(
            discovery=discovery_result,
            processing=processing_result,
            metadata={
                "source": source.value,
                "portal": portal.name,
                "authenticated": True,
                "test_mode": True,
            },
        )


def test_complete_linkedin_discovery_pipeline(
    tmp_path: Path,
) -> None:
    """
    Verify the complete local LinkedIn discovery pipeline.

    The test validates:

        Browser
            ↓
        PortalSession
            ↓
        LinkedInPortalAdapter
            ↓
        Job extraction
            ↓
        DiscoveryResult
            ↓
        JobDiscoveryService
            ↓
        Repository persistence
    """

    html_file = _write_linkedin_fixture(
        tmp_path
    )

    repository = InMemoryJobRepository()

    discovery_service = JobDiscoveryService(
        repository
    )

    registry = JobPortalRegistry()

    registry.register(
        LocalLinkedInPortalAdapter()
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

            orchestrator = (
                LocalDiscoveryOrchestrator(
                    portal_registry=registry,
                    discovery_service=discovery_service,
                    session=session,
                )
            )

            criteria = JobSearchCriteria(
                keywords=(
                    "Data Analyst",
                ),
                locations=(
                    "Hyderabad",
                ),
                maximum_results=10,
            )

            result = orchestrator.discover(
                source=JobSourceType.LINKEDIN,
                criteria=criteria,
            )

    finally:
        engine.shutdown()

    # --------------------------------------------------------------
    # Discovery result
    # --------------------------------------------------------------

    assert result.discovery.source == (
        JobSourceType.LINKEDIN
    )

    assert result.discovery.total_found == 2

    assert len(
        result.discovery.jobs
    ) == 2

    # --------------------------------------------------------------
    # Persistence result
    # --------------------------------------------------------------

    assert (
        result.processing.persisted_count
        == 2
    )

    assert (
        result.processing.created_count
        == 2
    )

    assert (
        result.processing.updated_count
        == 0
    )

    assert (
        result.processing.failed_count
        == 0
    )

    # --------------------------------------------------------------
    # First discovered job
    # --------------------------------------------------------------

    first_job = (
        result.discovery.jobs[0]
    )

    assert first_job.external_id == (
        "100001"
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

    assert first_job.source == (
        JobSourceType.LINKEDIN
    )

    assert first_job.url == (
        "https://www.linkedin.com/jobs/view/100001/"
    )

    # --------------------------------------------------------------
    # Second discovered job
    # --------------------------------------------------------------

    second_job = (
        result.discovery.jobs[1]
    )

    assert second_job.external_id == (
        "100002"
    )

    assert second_job.title == (
        "Business Data Analyst"
    )

    assert second_job.company_name == (
        "Data Solutions Pvt Ltd"
    )

    assert second_job.location == (
        "Hyderabad, Telangana, India"
    )

    assert second_job.source == (
        JobSourceType.LINKEDIN
    )

    assert second_job.url == (
        "https://www.linkedin.com/jobs/view/100002/"
    )

    # --------------------------------------------------------------
    # Repository verification
    # --------------------------------------------------------------

    assert (
        repository.count_active(
            source=JobSourceType.LINKEDIN
        )
        == 2
    )

    persisted_jobs = (
        repository.list_active(
            source=JobSourceType.LINKEDIN,
            limit=10,
        )
    )

    assert len(
        persisted_jobs
    ) == 2

    persisted_external_ids = {
        job.external_id
        for job in persisted_jobs
    }

    assert persisted_external_ids == {
        "100001",
        "100002",
    }

    # --------------------------------------------------------------
    # Orchestration metadata
    # --------------------------------------------------------------

    assert result.metadata[
        "source"
    ] == "linkedin"

    assert result.metadata[
        "portal"
    ] == "LinkedIn"

    assert result.metadata[
        "authenticated"
    ] is True

    assert result.metadata[
        "test_mode"
    ] is True
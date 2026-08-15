"""
Discovery-to-application pipeline integration test.

This test verifies:

    DiscoveryResult
        ↓
    JobDiscoveryService
        ↓
    JobRepository
        ↓
    ApplicationPipelineService
        ↓
    Matching
        ↓
    Eligibility
        ↓
    Application Queue

No browser is opened and no real application is submitted.

Execution-layer concerns such as:
    - authentication
    - CAPTCHA
    - browser failures
    - manual browser intervention

are represented as eligibility gates here only when explicitly
provided to the application pipeline.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from src.modules.job_discovery.domain.application import (
    ApplicationEligibilityDecision,
)

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
)

from src.modules.job_discovery.domain.matching import (
    CandidateJobProfile,
)

from src.modules.job_discovery.domain.repositories.job.job_repository import (
    JobRepository,
)

from src.modules.job_discovery.services.application_pipeline import (
    ApplicationPipelineService,
)

from src.modules.job_discovery.services.discovery import (
    DiscoveryApplicationPipelineService,
    JobDiscoveryService,
)

from src.shared.config.constants import (
    DecisionType,
    JobSourceType,
)


# ----------------------------------------------------------------------
# In-memory repository
# ----------------------------------------------------------------------


class InMemoryJobRepository(JobRepository):
    """
    Test-only in-memory implementation of JobRepository.

    No database or external persistence system is used.
    """

    def __init__(self) -> None:
        self._jobs: dict[
            tuple[JobSourceType, str],
            DiscoveredJob,
        ] = {}

        self._internal_ids: dict[
            tuple[JobSourceType, str],
            UUID,
        ] = {}

    def create(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """Create a new discovered job."""

        key = (
            job.source,
            job.external_id,
        )

        if key in self._jobs:
            raise ValueError(
                "Job already exists."
            )

        self._jobs[key] = job
        self._internal_ids[key] = uuid4()

        return job

    def get_by_id(
        self,
        job_id: UUID,
    ) -> DiscoveredJob | None:
        """Return a job by internal UUID."""

        for key, internal_id in self._internal_ids.items():
            if internal_id == job_id:
                return self._jobs[key]

        return None

    def get_by_external_id(
        self,
        *,
        source: JobSourceType,
        external_job_id: str,
    ) -> DiscoveredJob | None:
        """Return a job by source and external job ID."""

        return self._jobs.get(
            (
                source,
                external_job_id,
            )
        )

    def upsert(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """Create or update a discovered job."""

        key = (
            job.source,
            job.external_id,
        )

        if key not in self._internal_ids:
            self._internal_ids[key] = uuid4()

        self._jobs[key] = job

        return job

    def update(
        self,
        job_id: UUID,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        """Update an existing discovered job."""

        key = (
            job.source,
            job.external_id,
        )

        if key not in self._jobs:
            raise KeyError(
                "Job does not exist."
            )

        self._jobs[key] = job
        self._internal_ids[key] = job_id

        return job

    def list_active(
        self,
        *,
        source: JobSourceType | None = None,
        limit: int = 100,
    ) -> list[DiscoveredJob]:
        """Return active discovered jobs."""

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
        Deactivate a job.

        The test repository does not maintain a separate active flag.
        """

        return None

    def count_active(
        self,
        *,
        source: JobSourceType | None = None,
    ) -> int:
        """Return the number of active jobs."""

        if source is None:
            return len(self._jobs)

        return sum(
            1
            for job in self._jobs.values()
            if job.source == source
        )

    @property
    def size(self) -> int:
        """Return number of persisted jobs."""

        return len(self._jobs)


# ----------------------------------------------------------------------
# Candidate profile
# ----------------------------------------------------------------------


def build_profile(
    *,
    minimum_match_score: float = 0.70,
) -> CandidateJobProfile:
    """
    Build a deterministic candidate profile.
    """

    return CandidateJobProfile(
        target_roles=(
            "Data Analyst",
            "Business Analyst",
        ),
        preferred_locations=(
            "Hyderabad",
            "Remote",
        ),
        preferred_remote_statuses=(
            "remote",
            "hybrid",
        ),
        required_skills=(
            "SQL",
            "Excel",
        ),
        preferred_skills=(
            "Power BI",
            "Python",
        ),
        excluded_roles=(),
        excluded_companies=(),
        minimum_experience_years=2.0,
        maximum_experience_years=5.0,
        minimum_match_score=minimum_match_score,
    )


# ----------------------------------------------------------------------
# Job factory
# ----------------------------------------------------------------------


def build_job(
    external_id: str,
    *,
    title: str = "Data Analyst",
    company: str = "Test Analytics Company",
    description: str = (
        "Data Analyst role requiring SQL Excel "
        "Power BI Python."
    ),
) -> DiscoveredJob:
    """
    Build a deterministic discovered job.
    """

    return DiscoveredJob(
        external_id=external_id,
        title=title,
        company_name=company,
        source=JobSourceType.LINKEDIN,
        url=(
            "https://www.linkedin.com/jobs/view/"
            + external_id
        ),
        location="Hyderabad",
        description=description,
        metadata={
            "test": True,
        },
    )


# ----------------------------------------------------------------------
# Service factory
# ----------------------------------------------------------------------


def build_service(
    repository: InMemoryJobRepository,
) -> DiscoveryApplicationPipelineService:
    """
    Build the complete discovery-to-application pipeline.
    """

    discovery_service = JobDiscoveryService(
        repository=repository
    )

    application_pipeline = (
        ApplicationPipelineService()
    )

    return DiscoveryApplicationPipelineService(
        discovery_service=discovery_service,
        application_pipeline=application_pipeline,
    )


# ----------------------------------------------------------------------
# Test 1 - successful pipeline
# ----------------------------------------------------------------------


def test_complete_success_pipeline() -> None:
    """
    Verify:

        discovery
        ↓
        persistence
        ↓
        matching
        ↓
        eligibility
        ↓
        queue
    """

    repository = InMemoryJobRepository()

    service = build_service(
        repository
    )

    job = build_job(
        "discovery-success-001"
    )

    discovery_result = DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=(job,),
        total_found=1,
        metadata={
            "batch": "success",
        },
    )

    result = service.process(
        discovery_result,
        build_profile(),
    )

    assert result.jobs_discovered == 1

    assert result.jobs_persisted == 1

    assert result.jobs_persistence_failed == 0

    assert result.jobs_evaluated == 1

    assert result.jobs_matched == 1

    assert result.jobs_queued == 1

    pipeline_result = (
        result.application_result.results[0]
    )

    assert (
        pipeline_result.match_result.decision
        == DecisionType.APPLY
    )

    assert (
        pipeline_result.queue_item
        is not None
    )

    assert (
        pipeline_result.eligibility_decision
    )

    print(
        "COMPLETE SUCCESS PIPELINE test passed"
    )

    print(
        "Discovered :",
        result.jobs_discovered,
    )

    print(
        "Persisted  :",
        result.jobs_persisted,
    )

    print(
        "Matched    :",
        result.jobs_matched,
    )

    print(
        "Queued     :",
        result.jobs_queued,
    )


# ----------------------------------------------------------------------
# Test 2 - low match
# ----------------------------------------------------------------------


def test_low_match_is_skipped() -> None:
    """
    Verify that a poorly matching job does not enter the queue.
    """

    repository = InMemoryJobRepository()

    service = build_service(
        repository
    )

    job = build_job(
        "low-match-001",
        title="Senior Java Developer",
        description=(
            "Senior Java Developer "
            "requiring Java Spring Boot."
        ),
    )

    result = service.process(
        DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=(job,),
            total_found=1,
        ),
        build_profile(
            minimum_match_score=0.90
        ),
    )

    assert result.jobs_discovered == 1

    assert result.jobs_persisted == 1

    assert result.jobs_evaluated == 1

    assert result.jobs_queued == 0

    pipeline_result = (
        result.application_result.results[0]
    )

    assert pipeline_result.queued is False

    print(
        "LOW MATCH skip test passed"
    )


# ----------------------------------------------------------------------
# Test 3 - CAPTCHA safety gate
# ----------------------------------------------------------------------


def test_captcha_gate() -> None:
    """
    Verify that CAPTCHA prevents a job from entering the application
    queue.

    CAPTCHA is represented explicitly by the eligibility layer as
    CAPTCHA_DETECTED.

    It is intentionally NOT counted as MANUAL_REVIEW because the
    application pipeline distinguishes these states.
    """

    repository = InMemoryJobRepository()

    service = build_service(
        repository
    )

    job = build_job(
        "captcha-gate-001"
    )

    result = service.process(
        DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=(job,),
            total_found=1,
        ),
        build_profile(),
        captcha_detected_ids={
            "captcha-gate-001"
        },
    )

    assert result.jobs_discovered == 1

    assert result.jobs_persisted == 1

    assert result.jobs_evaluated == 1

    assert result.jobs_queued == 0

    assert result.jobs_manual_review == 0

    assert len(
        result.application_result.results
    ) == 1

    pipeline_result = (
        result.application_result.results[0]
    )

    assert pipeline_result.queued is False

    assert (
        pipeline_result.eligibility_decision
        == ApplicationEligibilityDecision.CAPTCHA_DETECTED
    )

    assert (
        "CAPTCHA"
        in pipeline_result.reason
    )

    print(
        "CAPTCHA safety gate test passed"
    )

    print(
        "Queued:",
        pipeline_result.queued,
    )

    print(
        "Eligibility:",
        pipeline_result.eligibility_decision.value,
    )

    print(
        "Reason:",
        pipeline_result.reason,
    )


# ----------------------------------------------------------------------
# Test 4 - authentication safety gate
# ----------------------------------------------------------------------


def test_authentication_gate() -> None:
    """
    Verify that authentication requirements prevent queueing.
    """

    repository = InMemoryJobRepository()

    service = build_service(
        repository
    )

    job = build_job(
        "authentication-gate-001"
    )

    result = service.process(
        DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=(job,),
            total_found=1,
        ),
        build_profile(),
        authentication_required_ids={
            "authentication-gate-001"
        },
    )

    assert result.jobs_persisted == 1

    assert result.jobs_evaluated == 1

    assert result.jobs_queued == 0

    pipeline_result = (
        result.application_result.results[0]
    )

    assert pipeline_result.queued is False

    assert (
        pipeline_result.eligibility_decision
        == ApplicationEligibilityDecision.AUTHENTICATION_REQUIRED
    )

    print(
        "AUTHENTICATION safety gate test passed"
    )

    print(
        "Queued:",
        pipeline_result.queued,
    )

    print(
        "Eligibility:",
        pipeline_result.eligibility_decision.value,
    )


# ----------------------------------------------------------------------
# Test 5 - multiple jobs
# ----------------------------------------------------------------------


def test_multiple_jobs() -> None:
    """
    Verify batch discovery and application processing.
    """

    repository = InMemoryJobRepository()

    service = build_service(
        repository
    )

    jobs = (
        build_job(
            "batch-001"
        ),
        build_job(
            "batch-002",
            title="Business Analyst",
        ),
        build_job(
            "batch-003",
            title="Senior Java Developer",
            description=(
                "Java Spring Boot backend "
                "development."
            ),
        ),
    )

    result = service.process(
        DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=jobs,
            total_found=3,
        ),
        build_profile(),
    )

    assert result.jobs_discovered == 3

    assert result.jobs_persisted == 3

    assert result.jobs_evaluated == 3

    assert result.jobs_queued >= 1

    assert repository.size == 3

    print(
        "MULTI-JOB pipeline test passed"
    )

    print(
        "Jobs discovered:",
        result.jobs_discovered,
    )

    print(
        "Jobs persisted:",
        result.jobs_persisted,
    )

    print(
        "Jobs evaluated:",
        result.jobs_evaluated,
    )

    print(
        "Jobs queued:",
        result.jobs_queued,
    )


# ----------------------------------------------------------------------
# Test 6 - duplicate/upsert
# ----------------------------------------------------------------------


def test_duplicate_persistence_updates_existing_job() -> None:
    """
    Verify that the same discovered job is updated rather than
    duplicated in persistence.
    """

    repository = InMemoryJobRepository()

    service = build_service(
        repository
    )

    job = build_job(
        "duplicate-001"
    )

    first = service.process(
        DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=(job,),
            total_found=1,
        ),
        build_profile(),
    )

    second = service.process(
        DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=(job,),
            total_found=1,
        ),
        build_profile(),
    )

    assert (
        first.discovery_result.created_count
        == 1
    )

    assert (
        second.discovery_result.updated_count
        == 1
    )

    assert repository.size == 1

    print(
        "DUPLICATE/upsert protection test passed"
    )

    print(
        "Repository size:",
        repository.size,
    )


# ----------------------------------------------------------------------
# Test 7 - empty discovery
# ----------------------------------------------------------------------


def test_empty_discovery() -> None:
    """
    Verify that an empty discovery result produces no evaluations
    or queue entries.
    """

    repository = InMemoryJobRepository()

    service = build_service(
        repository
    )

    result = service.process(
        DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=(),
            total_found=0,
        ),
        build_profile(),
    )

    assert result.jobs_discovered == 0

    assert result.jobs_persisted == 0

    assert result.jobs_evaluated == 0

    assert result.jobs_queued == 0

    assert repository.size == 0

    print(
        "EMPTY discovery test passed"
    )


# ----------------------------------------------------------------------
# Test 8 - validation
# ----------------------------------------------------------------------


def test_validation() -> None:
    """
    Verify service-level input validation.
    """

    repository = InMemoryJobRepository()

    service = build_service(
        repository
    )

    try:
        service.process(
            None,
            build_profile(),
        )

    except ValueError as exc:
        assert (
            str(exc)
            == "discovery_result is required."
        )

    else:
        raise AssertionError(
            "Expected ValueError for missing discovery result."
        )

    print(
        "VALIDATION test passed"
    )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> None:
    print()
    print("=" * 70)
    print(
        "DISCOVERY → APPLICATION PIPELINE INTEGRATION TEST"
    )
    print("=" * 70)

    print()

    test_complete_success_pipeline()

    print()

    test_low_match_is_skipped()

    print()

    test_captcha_gate()

    print()

    test_authentication_gate()

    print()

    test_multiple_jobs()

    print()

    test_duplicate_persistence_updates_existing_job()

    print()

    test_empty_discovery()

    print()

    test_validation()

    print()
    print("=" * 70)
    print(
        "ALL DISCOVERY → APPLICATION PIPELINE TESTS PASSED"
    )
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()

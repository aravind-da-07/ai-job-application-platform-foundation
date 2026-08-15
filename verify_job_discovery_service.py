"""
Verification tests for JobDiscoveryService.

Uses an in-memory fake repository.

No PostgreSQL, Supabase, LinkedIn, browser, or network access
is required.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
)
from src.modules.job_discovery.domain.repositories.job.job_repository import (
    JobRepository,
)
from src.modules.job_discovery.services.discovery import (
    JobDiscoveryService,
)
from src.shared.config.constants import (
    JobSourceType,
)


class FakeJobRepository(JobRepository):
    """Minimal in-memory repository for service verification."""

    def __init__(self) -> None:
        self._jobs: dict[
            tuple[JobSourceType, str],
            tuple[UUID, DiscoveredJob],
        ] = {}

    def create(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        key = (
            job.source,
            job.external_id,
        )

        if key in self._jobs:
            raise ValueError(
                "Job already exists."
            )

        self._jobs[key] = (
            uuid4(),
            job,
        )

        return job

    def get_by_id(
        self,
        job_id: UUID,
    ) -> DiscoveredJob | None:
        for stored_id, job in self._jobs.values():
            if stored_id == job_id:
                return job

        return None

    def get_by_external_id(
        self,
        *,
        source: JobSourceType,
        external_job_id: str,
    ) -> DiscoveredJob | None:
        record = self._jobs.get(
            (
                source,
                external_job_id,
            )
        )

        if record is None:
            return None

        return record[1]

    def upsert(
        self,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        key = (
            job.source,
            job.external_id,
        )

        existing = self._jobs.get(key)

        if existing is None:
            self._jobs[key] = (
                uuid4(),
                job,
            )
        else:
            self._jobs[key] = (
                existing[0],
                job,
            )

        return job

    def update(
        self,
        job_id: UUID,
        job: DiscoveredJob,
    ) -> DiscoveredJob:
        for key, (
            stored_id,
            _,
        ) in self._jobs.items():

            if stored_id == job_id:
                self._jobs[key] = (
                    stored_id,
                    job,
                )

                return job

        raise ValueError(
            "Job not found."
        )

    def list_active(
        self,
        *,
        source: JobSourceType | None = None,
        limit: int = 100,
    ) -> list[DiscoveredJob]:

        jobs = [
            job
            for (
                stored_source,
                _,
            ), (
                _,
                job,
            ) in self._jobs.items()
            if (
                source is None
                or stored_source == source
            )
        ]

        return jobs[:limit]

    def deactivate(
        self,
        job_id: UUID,
    ) -> None:
        raise NotImplementedError

    def count_active(
        self,
        *,
        source: JobSourceType | None = None,
    ) -> int:
        return len(
            self.list_active(
                source=source
            )
        )


def create_job(
    external_id: str,
    title: str,
    company: str = "Test Company",
) -> DiscoveredJob:
    """Create a valid test job."""

    return DiscoveredJob(
        external_id=external_id,
        title=title,
        company_name=company,
        source=JobSourceType.LINKEDIN,
        url=(
            f"https://www.linkedin.com/jobs/"
            f"view/{external_id}"
        ),
        metadata={
            "test": True,
        },
    )


def main() -> None:

    print()
    print("=" * 70)
    print("JOB DISCOVERY SERVICE INTEGRATION TEST")
    print("=" * 70)

    repository = FakeJobRepository()

    service = JobDiscoveryService(
        repository
    )

    # ==============================================================
    # 1
    # ==============================================================

    print()
    print(
        "[1/8] Testing service configuration..."
    )

    assert service.configured is True

    print(
        "CONFIGURATION test passed"
    )

    # ==============================================================
    # 2
    # ==============================================================

    print()
    print(
        "[2/8] Testing single-job discovery..."
    )

    job = create_job(
        "discovery-job-001",
        "Data Analyst",
    )

    discovery = DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=(job,),
        total_found=1,
        metadata={
            "search": "data analyst"
        },
    )

    result = service.process(
        discovery
    )

    assert result.jobs_received == 1
    assert result.persisted_count == 1
    assert result.created_count == 1
    assert result.updated_count == 0
    assert result.failed_count == 0

    print(
        "SINGLE JOB persistence successful"
    )
    print(
        "Persisted:",
        result.persisted_count,
    )

    # ==============================================================
    # 3
    # ==============================================================

    print()
    print(
        "[3/8] Testing duplicate/upsert handling..."
    )

    updated_job = create_job(
        "discovery-job-001",
        "Senior Data Analyst",
    )

    duplicate_discovery = DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=(updated_job,),
        total_found=1,
    )

    duplicate_result = service.process(
        duplicate_discovery
    )

    assert duplicate_result.persisted_count == 1
    assert duplicate_result.created_count == 0
    assert duplicate_result.updated_count == 1

    stored = service.get_existing_job(
        source=JobSourceType.LINKEDIN,
        external_job_id="discovery-job-001",
    )

    assert stored is not None
    assert stored.title == "Senior Data Analyst"

    print(
        "UPSERT handling successful"
    )
    print(
        "Created:",
        duplicate_result.created_count,
    )
    print(
        "Updated:",
        duplicate_result.updated_count,
    )

    # ==============================================================
    # 4
    # ==============================================================

    print()
    print(
        "[4/8] Testing batch discovery..."
    )

    jobs = (
        create_job(
            "discovery-job-002",
            "Business Analyst",
        ),
        create_job(
            "discovery-job-003",
            "BI Analyst",
        ),
        create_job(
            "discovery-job-004",
            "SQL Analyst",
        ),
    )

    batch_discovery = DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=jobs,
        total_found=3,
        metadata={
            "batch": True,
        },
    )

    batch_result = service.process(
        batch_discovery
    )

    assert batch_result.jobs_received == 3
    assert batch_result.persisted_count == 3
    assert batch_result.created_count == 3
    assert batch_result.failed_count == 0

    print(
        "BATCH discovery successful"
    )
    print(
        "Jobs received:",
        batch_result.jobs_received,
    )
    print(
        "Jobs persisted:",
        batch_result.persisted_count,
    )

    # ==============================================================
    # 5
    # ==============================================================

    print()
    print(
        "[5/8] Testing metadata preservation..."
    )

    metadata_discovery = DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=(
            create_job(
                "discovery-job-005",
                "Data Engineer",
            ),
        ),
        total_found=1,
        metadata={
            "keyword": "data engineer",
            "location": "Hyderabad",
        },
    )

    metadata_result = service.process(
        metadata_discovery
    )

    assert (
        metadata_result.metadata[
            "keyword"
        ]
        == "data engineer"
    )

    assert (
        metadata_result.metadata[
            "location"
        ]
        == "Hyderabad"
    )

    print(
        "METADATA preservation successful"
    )

    # ==============================================================
    # 6
    # ==============================================================

    print()
    print(
        "[6/8] Testing source validation..."
    )

    try:
        invalid_job = DiscoveredJob(
            external_id="invalid-source-job",
            title="Invalid Source",
            company_name="Test Company",
            source=JobSourceType.INDEED,
            url="https://example.com/job",
        )

        invalid_result = DiscoveryResult(
            source=JobSourceType.LINKEDIN,
            jobs=(invalid_job,),
            total_found=1,
        )

        service.process(
            invalid_result
        )

    except ValueError as exc:
        assert (
            "same source"
            in str(exc)
        )

        print(
            "SOURCE validation successful"
        )
        print(
            "Reason:",
            str(exc),
        )

    else:
        raise AssertionError(
            "Expected source validation error."
        )

    # ==============================================================
    # 7
    # ==============================================================

    print()
    print(
        "[7/8] Testing empty discovery..."
    )

    empty_discovery = DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=(),
        total_found=0,
    )

    empty_result = service.process(
        empty_discovery
    )

    assert (
        empty_result.jobs_received
        == 0
    )

    assert (
        empty_result.persisted_count
        == 0
    )

    print(
        "EMPTY discovery handling successful"
    )

    # ==============================================================
    # 8
    # ==============================================================

    print()
    print(
        "[8/8] Testing single-job API..."
    )

    single_job = create_job(
        "discovery-job-006",
        "Product Analyst",
    )

    persisted = service.process_job(
        single_job
    )

    assert (
        persisted.external_id
        == "discovery-job-006"
    )

    retrieved = service.get_existing_job(
        source=JobSourceType.LINKEDIN,
        external_job_id="discovery-job-006",
    )

    assert retrieved is not None
    assert (
        retrieved.external_id
        == "discovery-job-006"
    )

    print(
        "SINGLE JOB API handling successful"
    )

    print()
    print("=" * 70)
    print(
        "JOB DISCOVERY SERVICE TEST PASSED"
    )
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
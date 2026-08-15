"""
Integration tests for the SQLAlchemy discovered-job repository.

These tests use the shared SQLite test database fixture from conftest.py.

They verify:

- create
- get_by_external_id
- upsert
- update
- list_active
- source filtering
- deactivate
- count_active
- duplicate protection
- identity protection
- metadata round-trip
- domain/ORM mapping
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.infrastructure.models.job_model import (
    JobModel,
)
from src.modules.job_discovery.infrastructure.repositories.job.job_repository_impl import (
    SQLAlchemyJobRepository,
)
from src.shared.config.constants import JobSourceType


def build_job(
    external_id: str,
    *,
    source: JobSourceType = JobSourceType.LINKEDIN,
    title: str = "Senior Data Analyst",
    company_name: str = "Test Company",
    url: str | None = None,
    location: str | None = "Hyderabad, India",
    description: str | None = (
        "Data analysis, SQL, Python, Excel and Power BI."
    ),
    posted_at: str | None = "2026-08-14T10:00:00+00:00",
    salary_min: float | None = 700000.0,
    salary_max: float | None = 1200000.0,
    salary_currency: str | None = "INR",
    metadata: dict | None = None,
) -> DiscoveredJob:
    """Build a valid domain job for repository tests."""

    return DiscoveredJob(
        external_id=external_id,
        title=title,
        company_name=company_name,
        source=source,
        url=url
        or (
            "https://www.linkedin.com/jobs/view/"
            f"{external_id}"
        ),
        location=location,
        description=description,
        posted_at=posted_at,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        metadata=metadata
        or {
            "test": True,
            "portal": "linkedin",
        },
    )


@pytest.fixture()
def repository(
    db_session: Session,
) -> SQLAlchemyJobRepository:
    """Create a repository backed by the isolated test session."""

    return SQLAlchemyJobRepository(db_session)


def get_persisted_model(
    repository: SQLAlchemyJobRepository,
    external_id: str,
    source: JobSourceType = JobSourceType.LINKEDIN,
) -> JobModel:
    """
    Retrieve the ORM model for tests that need its internal UUID.

    The domain DiscoveredJob intentionally exposes the external portal
    identity rather than the database UUID.
    """

    model = (
        repository._session.query(JobModel)
        .filter(
            JobModel.external_job_id == external_id,
            JobModel.source == source,
        )
        .one()
    )

    return model


def test_create_and_get_by_external_id(
    repository: SQLAlchemyJobRepository,
) -> None:
    """A created job should be retrievable by source/external ID."""

    job = build_job("repo-create-001")

    persisted = repository.create(job)

    assert persisted.external_id == "repo-create-001"
    assert persisted.title == "Senior Data Analyst"
    assert persisted.company_name == "Test Company"
    assert persisted.source == JobSourceType.LINKEDIN

    fetched = repository.get_by_external_id(
        source=JobSourceType.LINKEDIN,
        external_job_id="repo-create-001",
    )

    assert fetched is not None
    assert fetched.external_id == persisted.external_id
    assert fetched.title == persisted.title
    assert fetched.company_name == persisted.company_name
    assert fetched.url == persisted.url


def test_get_by_external_id_returns_none_when_missing(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Unknown source/external identity should return None."""

    result = repository.get_by_external_id(
        source=JobSourceType.LINKEDIN,
        external_job_id="does-not-exist",
    )

    assert result is None


def test_create_preserves_job_data(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Repository mapping should preserve important domain fields."""

    original = build_job(
        "repo-mapping-001",
        title="Business Data Analyst",
        company_name="Mapping Corporation",
        location="Bengaluru, India",
        description="SQL and Power BI analytics role.",
        salary_min=600000.0,
        salary_max=1000000.0,
        salary_currency="INR",
        metadata={
            "portal": "linkedin",
            "test_case": "mapping",
            "priority": "high",
        },
    )

    persisted = repository.create(original)

    assert persisted.external_id == original.external_id
    assert persisted.title == original.title
    assert persisted.company_name == original.company_name
    assert persisted.url == original.url
    assert persisted.location == original.location
    assert persisted.description == original.description
    assert persisted.salary_min == original.salary_min
    assert persisted.salary_max == original.salary_max
    assert persisted.salary_currency == original.salary_currency
    assert persisted.metadata == original.metadata


def test_duplicate_create_is_rejected(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Creating the same source/external ID twice must fail."""

    first = build_job("repo-duplicate-001")

    repository.create(first)

    duplicate = build_job(
        "repo-duplicate-001",
        title="Different Title",
    )

    with pytest.raises(
        ValueError,
        match="Job already exists",
    ):
        repository.create(duplicate)


def test_upsert_creates_new_job(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Upsert should create a job when no matching identity exists."""

    job = build_job("repo-upsert-create-001")

    result = repository.upsert(job)

    assert result.external_id == "repo-upsert-create-001"
    assert result.title == job.title

    fetched = repository.get_by_external_id(
        source=JobSourceType.LINKEDIN,
        external_job_id="repo-upsert-create-001",
    )

    assert fetched is not None
    assert fetched.title == job.title


def test_upsert_updates_existing_job(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Upsert should update an existing source/external ID."""

    original = build_job(
        "repo-upsert-update-001",
        title="Junior Data Analyst",
        company_name="Original Company",
    )

    repository.create(original)

    updated = build_job(
        "repo-upsert-update-001",
        title="Senior Data Analyst",
        company_name="Updated Company",
        description="Updated job description.",
    )

    result = repository.upsert(updated)

    assert result.external_id == original.external_id
    assert result.title == "Senior Data Analyst"
    assert result.company_name == "Updated Company"
    assert result.description == "Updated job description."

    fetched = repository.get_by_external_id(
        source=JobSourceType.LINKEDIN,
        external_job_id="repo-upsert-update-001",
    )

    assert fetched is not None
    assert fetched.title == "Senior Data Analyst"
    assert fetched.company_name == "Updated Company"


def test_update_existing_job(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Update should modify an existing job by internal UUID."""

    original = build_job(
        "repo-update-001",
        title="Data Analyst",
        company_name="Original Company",
    )

    repository.create(original)

    model = get_persisted_model(
        repository,
        "repo-update-001",
    )

    assert isinstance(model.id, UUID)

    updated = build_job(
        "repo-update-001",
        title="Senior Data Analyst",
        company_name="Updated Company",
        location="Pune, India",
    )

    result = repository.update(
        model.id,
        updated,
    )

    assert result.external_id == "repo-update-001"
    assert result.title == "Senior Data Analyst"
    assert result.company_name == "Updated Company"
    assert result.location == "Pune, India"


def test_update_missing_job_is_rejected(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Updating a nonexistent UUID must fail."""

    job = build_job("repo-update-missing-001")

    with pytest.raises(
        ValueError,
        match="was not found",
    ):
        repository.update(
            uuid4(),
            job,
        )


def test_update_cannot_change_source(
    repository: SQLAlchemyJobRepository,
) -> None:
    """A job's portal source must remain immutable."""

    original = build_job(
        "repo-identity-source-001",
        source=JobSourceType.LINKEDIN,
    )

    repository.create(original)

    model = get_persisted_model(
        repository,
        "repo-identity-source-001",
    )

    source_members = list(JobSourceType)

    alternative_sources = [
        source
        for source in source_members
        if source != JobSourceType.LINKEDIN
    ]

    if not alternative_sources:
        pytest.skip(
            "JobSourceType contains only LINKEDIN; "
            "source identity-change test is not applicable."
        )

    changed_source = build_job(
        "repo-identity-source-001",
        source=alternative_sources[0],
    )

    with pytest.raises(
        ValueError,
        match="Job source cannot be changed",
    ):
        repository.update(
            model.id,
            changed_source,
        )


def test_update_cannot_change_external_id(
    repository: SQLAlchemyJobRepository,
) -> None:
    """A job's external portal ID must remain immutable."""

    original = build_job(
        "repo-identity-external-001",
    )

    repository.create(original)

    model = get_persisted_model(
        repository,
        "repo-identity-external-001",
    )

    changed_identity = build_job(
        "repo-identity-external-CHANGED",
    )

    with pytest.raises(
        ValueError,
        match="External job ID cannot be changed",
    ):
        repository.update(
            model.id,
            changed_identity,
        )


def test_list_active_returns_active_jobs(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Only active jobs should be returned."""

    first = build_job(
        "repo-list-001",
        title="First Analyst",
    )

    second = build_job(
        "repo-list-002",
        title="Second Analyst",
    )

    third = build_job(
        "repo-list-003",
        title="Third Analyst",
    )

    repository.create(first)
    repository.create(second)
    repository.create(third)

    active_jobs = repository.list_active()

    external_ids = {
        job.external_id
        for job in active_jobs
    }

    assert "repo-list-001" in external_ids
    assert "repo-list-002" in external_ids
    assert "repo-list-003" in external_ids


def test_list_active_respects_limit(
    repository: SQLAlchemyJobRepository,
) -> None:
    """The active-job query should respect its limit."""

    for index in range(5):
        repository.create(
            build_job(
                f"repo-limit-{index:03d}",
                title=f"Analyst {index}",
            )
        )

    jobs = repository.list_active(limit=2)

    assert len(jobs) == 2


def test_list_active_rejects_invalid_limit(
    repository: SQLAlchemyJobRepository,
) -> None:
    """A non-positive limit must be rejected."""

    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        repository.list_active(limit=0)


def test_source_filter(
    repository: SQLAlchemyJobRepository,
) -> None:
    """list_active should support filtering by source."""

    linkedin_job = build_job(
        "repo-source-linkedin-001",
        source=JobSourceType.LINKEDIN,
    )

    repository.create(linkedin_job)

    linkedin_jobs = repository.list_active(
        source=JobSourceType.LINKEDIN,
    )

    assert len(linkedin_jobs) == 1
    assert linkedin_jobs[0].external_id == (
        "repo-source-linkedin-001"
    )


def test_deactivate_removes_job_from_active_results(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Deactivated jobs must no longer appear in active queries."""

    job = build_job(
        "repo-deactivate-001",
    )

    repository.create(job)

    model = get_persisted_model(
        repository,
        "repo-deactivate-001",
    )

    repository.deactivate(model.id)

    active_jobs = repository.list_active()

    assert not any(
        item.external_id == "repo-deactivate-001"
        for item in active_jobs
    )


def test_deactivate_missing_job_is_rejected(
    repository: SQLAlchemyJobRepository,
) -> None:
    """Deactivating an unknown UUID must fail."""

    with pytest.raises(
        ValueError,
        match="was not found",
    ):
        repository.deactivate(uuid4())


def test_count_active(
    repository: SQLAlchemyJobRepository,
) -> None:
    """count_active should return only active jobs."""

    first = build_job("repo-count-001")
    second = build_job("repo-count-002")
    third = build_job("repo-count-003")

    repository.create(first)
    repository.create(second)
    repository.create(third)

    assert repository.count_active() == 3

    model = get_persisted_model(
        repository,
        "repo-count-002",
    )

    repository.deactivate(model.id)

    assert repository.count_active() == 2


def test_count_active_by_source(
    repository: SQLAlchemyJobRepository,
) -> None:
    """count_active should support source filtering."""

    repository.create(
        build_job(
            "repo-count-source-001",
            source=JobSourceType.LINKEDIN,
        )
    )

    assert (
        repository.count_active(
            source=JobSourceType.LINKEDIN,
        )
        == 1
    )


def test_deactivated_job_can_be_reactivated_by_upsert(
    repository: SQLAlchemyJobRepository,
) -> None:
    """
    Upsert should reactivate an existing inactive job because the
    repository mapping sets is_active=True.
    """

    job = build_job(
        "repo-reactivate-001",
    )

    repository.create(job)

    model = get_persisted_model(
        repository,
        "repo-reactivate-001",
    )

    repository.deactivate(model.id)

    assert repository.count_active() == 0

    updated = build_job(
        "repo-reactivate-001",
        title="Reactivated Senior Data Analyst",
    )

    result = repository.upsert(updated)

    assert result.title == "Reactivated Senior Data Analyst"
    assert repository.count_active() == 1


def test_metadata_round_trip(
    repository: SQLAlchemyJobRepository,
) -> None:
    """JSON metadata should survive domain/ORM conversion."""

    metadata = {
        "portal": "linkedin",
        "easy_apply": True,
        "search_keyword": "data analyst",
        "ranking": 1,
        "nested": {
            "source": "integration-test",
        },
    }

    job = build_job(
        "repo-metadata-001",
        metadata=metadata,
    )

    repository.create(job)

    fetched = repository.get_by_external_id(
        source=JobSourceType.LINKEDIN,
        external_job_id="repo-metadata-001",
    )

    assert fetched is not None
    assert fetched.metadata == metadata
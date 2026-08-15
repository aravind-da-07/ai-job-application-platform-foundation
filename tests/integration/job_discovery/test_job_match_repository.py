"""
Integration tests for the SQLAlchemy job-match repository.

These tests verify persistence and retrieval of transparent job-matching
results using the isolated SQLite database fixture.

Coverage:

- create
- get_by_id
- get_for_job
- resume-aware lookup
- list_for_user
- decision filtering
- limit validation
- missing match handling
- duplicate protection
- score persistence
- breakdown persistence
- explanation persistence
- metadata persistence
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.domain.matching.job_matching import (
    JobMatchBreakdown,
    JobMatchResult,
)
from src.modules.job_discovery.domain.repositories.job.job_match_repository import (
    JobMatchRepository,
)
from src.modules.job_discovery.infrastructure.models.job_model import (
    JobMatchModel,
    JobModel,
)
from src.modules.job_discovery.infrastructure.repositories.job.job_match_repository_impl import (
    SQLAlchemyJobMatchRepository,
)
from src.modules.job_discovery.infrastructure.repositories.job.job_repository_impl import (
    SQLAlchemyJobRepository,
)
from src.modules.users.infrastructure.models.user_model import (
    UserModel,
)
from src.shared.config.constants import JobSourceType


# ----------------------------------------------------------------------
# Test data builders
# ----------------------------------------------------------------------


def build_job(
    external_id: str,
    *,
    title: str = "Senior Data Analyst",
    company_name: str = "Test Company",
) -> DiscoveredJob:
    """Build a valid discovered job for match repository tests."""

    return DiscoveredJob(
        external_id=external_id,
        title=title,
        company_name=company_name,
        source=JobSourceType.LINKEDIN,
        url=(
            "https://www.linkedin.com/jobs/view/"
            f"{external_id}"
        ),
        location="Hyderabad, India",
        description=(
            "Senior Data Analyst role requiring "
            "SQL, Python, Excel and Power BI."
        ),
        posted_at="2026-08-14T10:00:00+00:00",
        salary_min=700000.0,
        salary_max=1200000.0,
        salary_currency="INR",
        metadata={
            "portal": "linkedin",
            "test": True,
        },
    )


def build_match_result(
    external_job_id: str,
    *,
    overall_score: float = 0.94,
    decision: str = "apply",
    reason: str = (
        "Strong match based on role, skills, "
        "location and experience."
    ),
    metadata: dict | None = None,
) -> JobMatchResult:
    """Build a complete transparent matching result."""

    breakdown = JobMatchBreakdown(
        title_score=0.95,
        skill_score=0.92,
        location_score=0.90,
        remote_score=0.85,
        experience_score=0.93,
        matched_skills=(
            "SQL",
            "Python",
            "Excel",
            "Power BI",
        ),
        missing_required_skills=(
            "Tableau",
        ),
        matched_roles=(
            "Data Analyst",
            "Senior Data Analyst",
        ),
        excluded_reasons=(),
        metadata={
            "breakdown_source": "integration_test",
            "scoring_version": "1.0",
        },
    )

    return JobMatchResult(
        external_job_id=external_job_id,
        overall_score=overall_score,
        decision=decision,
        breakdown=breakdown,
        reason=reason,
        metadata=metadata
        or {
            "test_case": "job_match_repository",
            "model_version": "1.0",
        },
    )


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture()
def repository(
    db_session: Session,
) -> SQLAlchemyJobMatchRepository:
    """Create a job-match repository using the test session."""

    return SQLAlchemyJobMatchRepository(db_session)


@pytest.fixture()
def job_repository(
    db_session: Session,
) -> SQLAlchemyJobRepository:
    """Create a job repository using the test session."""

    return SQLAlchemyJobRepository(db_session)


def create_user(
    session: Session,
    *,
    full_name: str = "Test Candidate",
    email: str | None = None,
) -> UserModel:
    """Create a valid test user."""

    user = UserModel(
        full_name=full_name,
        email=email
        or f"{uuid4()}@example.com",
    )

    session.add(user)
    session.flush()

    return user


def create_job(
    repository: SQLAlchemyJobRepository,
    external_id: str,
) -> tuple[DiscoveredJob, UUID]:
    """Create a job and return its domain object plus internal UUID."""

    job = build_job(external_id)

    repository.create(job)

    model = (
        repository._session.query(JobModel)
        .filter(
            JobModel.external_job_id == external_id,
            JobModel.source == JobSourceType.LINKEDIN,
        )
        .one()
    )

    return job, model.id


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def test_create_match(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """A valid match should be persisted successfully."""

    job, job_id = create_job(
        job_repository,
        "match-create-001",
    )

    user = create_user(
        db_session,
        full_name="Create Match Candidate",
    )

    result = build_match_result(
        job.external_id,
    )

    match_id = repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=result,
    )

    assert isinstance(match_id, UUID)

    model = db_session.get(
        JobMatchModel,
        match_id,
    )

    assert model is not None
    assert model.job_id == job_id
    assert model.user_id == user.id
    assert model.resume_id is None
    assert float(model.overall_score) == pytest.approx(
        0.94
    )
    assert model.decision == "apply"
    assert model.reason == result.reason


def test_get_by_id(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """A persisted match should be retrievable by match UUID."""

    job, job_id = create_job(
        job_repository,
        "match-get-id-001",
    )

    user = create_user(
        db_session,
        full_name="Get Match Candidate",
    )

    original = build_match_result(
        job.external_id,
    )

    match_id = repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=original,
    )

    fetched = repository.get_by_id(match_id)

    assert fetched is not None
    assert fetched.external_job_id == (
        job.external_id
    )
    assert fetched.overall_score == pytest.approx(
        original.overall_score
    )
    assert fetched.decision == original.decision
    assert fetched.reason == original.reason


def test_get_by_id_returns_none_for_missing_match(
    repository: SQLAlchemyJobMatchRepository,
) -> None:
    """An unknown match UUID should return None."""

    result = repository.get_by_id(
        uuid4(),
    )

    assert result is None


def test_get_for_job_without_resume(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """A match without a resume should be retrievable."""

    job, job_id = create_job(
        job_repository,
        "match-for-job-001",
    )

    user = create_user(
        db_session,
        full_name="Job Lookup Candidate",
    )

    original = build_match_result(
        job.external_id,
    )

    repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=original,
    )

    fetched = repository.get_for_job(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
    )

    assert fetched is not None
    assert fetched.external_job_id == (
        job.external_id
    )
    assert fetched.overall_score == pytest.approx(
        original.overall_score
    )


def test_get_for_job_does_not_mix_users(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """A user's match must not be returned for another user."""

    job, job_id = create_job(
        job_repository,
        "match-user-isolation-001",
    )

    first_user = create_user(
        db_session,
        full_name="First Candidate",
    )

    second_user = create_user(
        db_session,
        full_name="Second Candidate",
    )

    result = build_match_result(
        job.external_id,
    )

    repository.create(
        job_id=job_id,
        user_id=first_user.id,
        resume_id=None,
        result=result,
    )

    fetched = repository.get_for_job(
        job_id=job_id,
        user_id=second_user.id,
        resume_id=None,
    )

    assert fetched is None


def test_get_for_job_does_not_mix_jobs(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """A match for one job must not be returned for another job."""

    first_job, first_job_id = create_job(
        job_repository,
        "match-job-isolation-001",
    )

    second_job, second_job_id = create_job(
        job_repository,
        "match-job-isolation-002",
    )

    user = create_user(
        db_session,
        full_name="Job Isolation Candidate",
    )

    result = build_match_result(
        first_job.external_id,
    )

    repository.create(
        job_id=first_job_id,
        user_id=user.id,
        resume_id=None,
        result=result,
    )

    fetched = repository.get_for_job(
        job_id=second_job_id,
        user_id=user.id,
        resume_id=None,
    )

    assert fetched is None


def test_list_for_user(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """All persisted matches for a user should be returned."""

    user = create_user(
        db_session,
        full_name="List Candidate",
    )

    jobs = []

    for index in range(3):
        job, job_id = create_job(
            job_repository,
            f"match-list-{index:03d}",
        )

        jobs.append(
            (job, job_id)
        )

    for job, job_id in jobs:
        repository.create(
            job_id=job_id,
            user_id=user.id,
            resume_id=None,
            result=build_match_result(
                job.external_id,
            ),
        )

    matches = repository.list_for_user(
        user_id=user.id,
    )

    assert len(matches) == 3

    external_ids = {
        match.external_job_id
        for match in matches
    }

    assert external_ids == {
        "match-list-000",
        "match-list-001",
        "match-list-002",
    }


def test_list_for_user_filters_by_decision(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """Decision filtering should return only matching decisions."""

    user = create_user(
        db_session,
        full_name="Decision Filter Candidate",
    )

    apply_job, apply_job_id = create_job(
        job_repository,
        "match-decision-apply-001",
    )

    skip_job, skip_job_id = create_job(
        job_repository,
        "match-decision-skip-001",
    )

    review_job, review_job_id = create_job(
        job_repository,
        "match-decision-review-001",
    )

    repository.create(
        job_id=apply_job_id,
        user_id=user.id,
        resume_id=None,
        result=build_match_result(
            apply_job.external_id,
            decision="apply",
            overall_score=0.94,
            reason="Strong match.",
        ),
    )

    repository.create(
        job_id=skip_job_id,
        user_id=user.id,
        resume_id=None,
        result=build_match_result(
            skip_job.external_id,
            decision="skip",
            overall_score=0.42,
            reason="Insufficient match score.",
        ),
    )

    repository.create(
        job_id=review_job_id,
        user_id=user.id,
        resume_id=None,
        result=build_match_result(
            review_job.external_id,
            decision="manual_review",
            overall_score=0.76,
            reason="Manual review required.",
        ),
    )

    apply_matches = repository.list_for_user(
        user_id=user.id,
        decision="apply",
    )

    assert len(apply_matches) == 1
    assert apply_matches[0].external_job_id == (
        apply_job.external_id
    )
    assert apply_matches[0].decision == "apply"

    skip_matches = repository.list_for_user(
        user_id=user.id,
        decision="skip",
    )

    assert len(skip_matches) == 1
    assert skip_matches[0].external_job_id == (
        skip_job.external_id
    )
    assert skip_matches[0].decision == "skip"

    review_matches = repository.list_for_user(
        user_id=user.id,
        decision="manual_review",
    )

    assert len(review_matches) == 1
    assert review_matches[0].external_job_id == (
        review_job.external_id
    )
    assert review_matches[0].decision == "manual_review"


def test_list_for_user_respects_limit(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """The list operation should respect its requested limit."""

    user = create_user(
        db_session,
        full_name="Limit Candidate",
    )

    for index in range(5):
        job, job_id = create_job(
            job_repository,
            f"match-limit-{index:03d}",
        )

        repository.create(
            job_id=job_id,
            user_id=user.id,
            resume_id=None,
            result=build_match_result(
                job.external_id,
            ),
        )

    matches = repository.list_for_user(
        user_id=user.id,
        limit=2,
    )

    assert len(matches) == 2


def test_list_for_user_rejects_invalid_limit(
    repository: SQLAlchemyJobMatchRepository,
    db_session: Session,
) -> None:
    """A non-positive limit must be rejected."""

    user = create_user(
        db_session,
        full_name="Invalid Limit Candidate",
    )

    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        repository.list_for_user(
            user_id=user.id,
            limit=0,
        )


def test_duplicate_match_is_rejected(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """The same job/user/resume combination cannot be duplicated."""

    job, job_id = create_job(
        job_repository,
        "match-duplicate-001",
    )

    user = create_user(
        db_session,
        full_name="Duplicate Candidate",
    )

    result = build_match_result(
        job.external_id,
    )

    repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=result,
    )

    with pytest.raises(
        ValueError,
        match="A job match already exists",
    ):
        repository.create(
            job_id=job_id,
            user_id=user.id,
            resume_id=None,
            result=result,
        )


def test_same_job_and_user_can_have_different_resume_matches(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """
    Different resume IDs represent different match identities.

    We create resume UUIDs directly here because this repository test
    only needs to verify JobMatchRepository identity behavior.
    """

    job, job_id = create_job(
        job_repository,
        "match-resume-identity-001",
    )

    user = create_user(
        db_session,
        full_name="Resume Identity Candidate",
    )

    first_resume_id = uuid4()
    second_resume_id = uuid4()

    result = build_match_result(
        job.external_id,
    )

    first_match_id = repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=first_resume_id,
        result=result,
    )

    second_match_id = repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=second_resume_id,
        result=result,
    )

    assert first_match_id != second_match_id

    first_match = repository.get_for_job(
        job_id=job_id,
        user_id=user.id,
        resume_id=first_resume_id,
    )

    second_match = repository.get_for_job(
        job_id=job_id,
        user_id=user.id,
        resume_id=second_resume_id,
    )

    assert first_match is not None
    assert second_match is not None


def test_null_resume_is_distinct_from_resume(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """A null-resume match is a different lookup from a resume match."""

    job, job_id = create_job(
        job_repository,
        "match-null-resume-001",
    )

    user = create_user(
        db_session,
        full_name="Null Resume Candidate",
    )

    resume_id = uuid4()

    result = build_match_result(
        job.external_id,
    )

    repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=result,
    )

    repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=resume_id,
        result=result,
    )

    null_resume_match = repository.get_for_job(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
    )

    resume_match = repository.get_for_job(
        job_id=job_id,
        user_id=user.id,
        resume_id=resume_id,
    )

    assert null_resume_match is not None
    assert resume_match is not None


def test_score_breakdown_persistence(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """All scoring components should survive persistence."""

    job, job_id = create_job(
        job_repository,
        "match-breakdown-001",
    )

    user = create_user(
        db_session,
        full_name="Breakdown Candidate",
    )

    original = build_match_result(
        job.external_id,
        overall_score=0.91,
    )

    match_id = repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=original,
    )

    fetched = repository.get_by_id(
        match_id,
    )

    assert fetched is not None

    assert fetched.overall_score == pytest.approx(
        0.91
    )

    assert fetched.breakdown.title_score == pytest.approx(
        0.95
    )

    assert fetched.breakdown.skill_score == pytest.approx(
        0.92
    )

    assert fetched.breakdown.location_score == pytest.approx(
        0.90
    )

    assert fetched.breakdown.remote_score == pytest.approx(
        0.85
    )

    assert fetched.breakdown.experience_score == pytest.approx(
        0.93
    )

    assert fetched.breakdown.matched_skills == (
        "SQL",
        "Python",
        "Excel",
        "Power BI",
    )

    assert fetched.breakdown.missing_required_skills == (
        "Tableau",
    )

    assert fetched.breakdown.matched_roles == (
        "Data Analyst",
        "Senior Data Analyst",
    )

    assert fetched.breakdown.excluded_reasons == ()


def test_reason_and_decision_persistence(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """Decision and explanation should survive persistence."""

    job, job_id = create_job(
        job_repository,
        "match-reason-001",
    )

    user = create_user(
        db_session,
        full_name="Reason Candidate",
    )

    original = build_match_result(
        job.external_id,
        overall_score=0.55,
        decision="manual_review",
        reason=(
            "Score is acceptable but the candidate "
            "requires manual review."
        ),
    )

    match_id = repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=original,
    )

    fetched = repository.get_by_id(
        match_id,
    )

    assert fetched is not None
    assert fetched.decision == "manual_review"
    assert fetched.reason == (
        "Score is acceptable but the candidate "
        "requires manual review."
    )


def test_metadata_persistence(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """Metadata from breakdown and result should survive round-trip."""

    job, job_id = create_job(
        job_repository,
        "match-metadata-001",
    )

    user = create_user(
        db_session,
        full_name="Metadata Candidate",
    )

    original = build_match_result(
        job.external_id,
        metadata={
            "candidate_source": "profile",
            "matching_version": "2.0",
            "threshold": 0.70,
        },
    )

    match_id = repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=original,
    )

    fetched = repository.get_by_id(
        match_id,
    )

    assert fetched is not None

    # The implementation intentionally merges breakdown metadata
    # and result metadata into the persisted metadata_json.
    assert fetched.metadata["breakdown_source"] == (
        "integration_test"
    )

    assert fetched.metadata["scoring_version"] == "1.0"

    assert fetched.metadata["candidate_source"] == (
        "profile"
    )

    assert fetched.metadata["matching_version"] == (
        "2.0"
    )

    assert fetched.metadata["threshold"] == pytest.approx(
        0.70
    )


def test_domain_mapping_uses_external_job_id(
    repository: SQLAlchemyJobMatchRepository,
    job_repository: SQLAlchemyJobRepository,
    db_session: Session,
) -> None:
    """
    Retrieved domain results must expose the portal external job ID,
    not the database UUID.

    This is explicitly part of the repository mapping contract.
    """

    job, job_id = create_job(
        job_repository,
        "linkedin-external-12345",
    )

    user = create_user(
        db_session,
        full_name="External ID Candidate",
    )

    match_id = repository.create(
        job_id=job_id,
        user_id=user.id,
        resume_id=None,
        result=build_match_result(
            job.external_id,
        ),
    )

    fetched = repository.get_by_id(
        match_id,
    )

    assert fetched is not None

    assert fetched.external_job_id == (
        "linkedin-external-12345"
    )

    assert fetched.external_job_id != str(job_id)


def test_repository_implements_domain_contract(
    repository: SQLAlchemyJobMatchRepository,
) -> None:
    """The concrete repository must implement the domain contract."""

    assert isinstance(
        repository,
        JobMatchRepository,
    )
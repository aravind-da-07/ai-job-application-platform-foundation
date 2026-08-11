"""
Application Pipeline Service Integration Test.

Tests:

    DiscoveredJob
        ↓
    JobMatchingService
        ↓
    ApplicationEligibilityService
        ↓
    ApplicationQueueService
"""

from __future__ import annotations

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.domain.matching import (
    CandidateJobProfile,
)
from src.modules.job_discovery.services.application_pipeline import (
    ApplicationPipelineService,
)
from src.shared.config.constants import (
    DecisionType,
    JobSourceType,
)


def decision_text(decision: object) -> str:
    """
    Safely convert a decision into display text.

    The matching service may expose the decision as either
    a DecisionType enum or its underlying string value.
    """

    if isinstance(decision, DecisionType):
        return decision.value

    return str(decision)


def create_job(
    external_id: str,
    *,
    title: str = "Data Analyst",
    company_name: str = "Test Company",
    location: str = "Hyderabad, Telangana, India",
) -> DiscoveredJob:
    """
    Create a deterministic test job.
    """

    return DiscoveredJob(
        external_id=external_id,
        title=title,
        company_name=company_name,
        source=JobSourceType.LINKEDIN,
        url=(
            "https://www.linkedin.com/jobs/view/"
            f"{external_id}"
        ),
        location=location,
        description=(
            "Data Analyst role requiring SQL, Excel, "
            "Power BI, Python and Data Analysis."
        ),
    )


def create_profile() -> CandidateJobProfile:
    """
    Create the candidate profile used by the tests.

    The excluded role is intentionally configured here so
    the pipeline can verify that matching respects explicit
    candidate exclusions.
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
        required_skills=(
            "SQL",
            "Excel",
        ),
        preferred_skills=(
            "Power BI",
            "Python",
            "Data Analysis",
        ),
        excluded_roles=(
            "Senior Data Scientist",
        ),
        excluded_companies=(
            "Excluded Test Company",
        ),
        minimum_match_score=0.70,
    )


def main() -> None:
    print()
    print("=" * 70)
    print("APPLICATION PIPELINE SERVICE INTEGRATION TEST")
    print("=" * 70)

    # ==============================================================
    # 1/10
    # ==============================================================

    print()
    print("[1/10] Creating candidate profile...")

    profile = create_profile()

    assert profile.target_roles == (
        "Data Analyst",
        "Business Analyst",
    )

    assert profile.minimum_match_score == 0.70

    assert "Senior Data Scientist" in (
        profile.excluded_roles
    )

    assert "Excluded Test Company" in (
        profile.excluded_companies
    )

    print("CANDIDATE PROFILE successful")
    print("Target roles:", profile.target_roles)
    print(
        "Preferred locations:",
        profile.preferred_locations,
    )
    print(
        "Required skills:",
        profile.required_skills,
    )
    print(
        "Excluded roles:",
        profile.excluded_roles,
    )
    print(
        "Excluded companies:",
        profile.excluded_companies,
    )
    print(
        "Minimum match score:",
        f"{profile.minimum_match_score:.0%}",
    )

    # ==============================================================
    # 2/10
    # ==============================================================

    print()
    print("[2/10] Creating application pipeline...")

    pipeline = ApplicationPipelineService()

    assert isinstance(
        pipeline,
        ApplicationPipelineService,
    )

    assert pipeline.queue_service.size == 0

    print("APPLICATION PIPELINE creation successful")
    print(
        "Initial queue size:",
        pipeline.queue_service.size,
    )

    # ==============================================================
    # 3/10
    # ==============================================================

    print()
    print("[3/10] Testing strong Data Analyst job...")

    job = create_job(
        "pipeline-test-001"
    )

    result = pipeline.process_job(
        job,
        profile,
        priority=10,
        metadata={
            "test": "strong_match",
        },
    )

    assert (
        result.match_result.decision
        == DecisionType.APPLY
        or result.match_result.decision
        == DecisionType.APPLY.value
    )

    assert result.queued is True
    assert result.queue_item is not None

    print("STRONG MATCH pipeline successful")
    print(
        "Match score:",
        f"{result.match_result.overall_score:.0%}",
    )
    print(
        "Match decision:",
        decision_text(
            result.match_result.decision
        ),
    )
    print(
        "Queued:",
        result.queued,
    )
    print(
        "Application ID:",
        result.queue_item.application_id,
    )

    # ==============================================================
    # 4/10
    # ==============================================================

    print()
    print("[4/10] Testing role-name variation...")

    variation_job = create_job(
        "pipeline-test-002",
        title="Business Data Analyst",
    )

    result = pipeline.process_job(
        variation_job,
        profile,
        priority=8,
    )

    assert result.queued is True

    assert (
        result.match_result.decision
        == DecisionType.APPLY
        or result.match_result.decision
        == DecisionType.APPLY.value
    )

    print("ROLE VARIATION pipeline successful")
    print(
        "Title:",
        variation_job.title,
    )
    print(
        "Match score:",
        f"{result.match_result.overall_score:.0%}",
    )
    print(
        "Queued:",
        result.queued,
    )

    # ==============================================================
    # 5/10
    # ==============================================================

    print()
    print("[5/10] Testing excluded role...")

    excluded_job = create_job(
        "pipeline-test-003",
        title="Senior Data Scientist",
    )

    result = pipeline.process_job(
        excluded_job,
        profile,
    )

    assert result.queued is False
    assert result.queue_item is None

    print("EXCLUDED ROLE pipeline successful")
    print(
        "Decision:",
        decision_text(
            result.match_result.decision
        ),
    )
    print(
        "Queued:",
        result.queued,
    )
    print(
        "Reason:",
        result.reason,
    )

    # ==============================================================
    # 6/10
    # ==============================================================

    print()
    print("[6/10] Testing duplicate job...")

    duplicate_job = create_job(
        "pipeline-test-001"
    )

    result = pipeline.process_job(
        duplicate_job,
        profile,
    )

    assert result.queued is False
    assert result.queue_item is None

    print("DUPLICATE pipeline handling successful")
    print(
        "Queued:",
        result.queued,
    )
    print(
        "Reason:",
        result.reason,
    )

    # ==============================================================
    # 7/10
    # ==============================================================

    print()
    print("[7/10] Testing inactive job...")

    inactive_job = create_job(
        "pipeline-test-004"
    )

    result = pipeline.process_job(
        inactive_job,
        profile,
        job_active=False,
    )

    assert result.queued is False
    assert result.queue_item is None

    print("INACTIVE JOB pipeline handling successful")
    print(
        "Queued:",
        result.queued,
    )
    print(
        "Reason:",
        result.reason,
    )

    # ==============================================================
    # 8/10
    # ==============================================================

    print()
    print("[8/10] Testing authentication requirement...")

    auth_job = create_job(
        "pipeline-test-005"
    )

    result = pipeline.process_job(
        auth_job,
        profile,
        authentication_required=True,
    )

    assert result.queued is False
    assert result.queue_item is None

    print("AUTHENTICATION pipeline handling successful")
    print(
        "Queued:",
        result.queued,
    )
    print(
        "Eligibility:",
        result.eligibility_decision.value,
    )
    print(
        "Reason:",
        result.reason,
    )

    # ==============================================================
    # 9/10
    # ==============================================================

    print()
    print("[9/10] Testing CAPTCHA handling...")

    captcha_job = create_job(
        "pipeline-test-006"
    )

    result = pipeline.process_job(
        captcha_job,
        profile,
        captcha_detected=True,
    )

    assert result.queued is False
    assert result.queue_item is None

    print("CAPTCHA pipeline handling successful")
    print(
        "Queued:",
        result.queued,
    )
    print(
        "Eligibility:",
        result.eligibility_decision.value,
    )
    print(
        "Reason:",
        result.reason,
    )

    # ==============================================================
    # 10/10
    # ==============================================================

    print()
    print("[10/10] Testing batch pipeline processing...")

    batch_jobs = (
        create_job(
            "batch-test-001",
            title="Data Analyst",
        ),
        create_job(
            "batch-test-002",
            title="Business Analyst",
        ),
        create_job(
            "batch-test-003",
            title="Senior Data Scientist",
        ),
        create_job(
            "batch-test-004",
            title="Data Analyst",
        ),
    )

    batch_result = pipeline.process_jobs(
        batch_jobs,
        profile,
        already_applied_ids={
            "batch-test-004",
        },
        inactive_job_ids=set(),
        authentication_required_ids=set(),
        captcha_detected_ids=set(),
        priority=5,
        metadata={
            "batch": "integration_test",
        },
    )

    assert batch_result.jobs_evaluated == 4

    assert batch_result.jobs_queued == 2

    assert batch_result.jobs_skipped == 2

    assert len(batch_result.results) == 4

    print("BATCH PIPELINE processing successful")
    print(
        "Jobs evaluated:",
        batch_result.jobs_evaluated,
    )
    print(
        "Jobs matched:",
        batch_result.jobs_matched,
    )
    print(
        "Jobs queued:",
        batch_result.jobs_queued,
    )
    print(
        "Jobs skipped:",
        batch_result.jobs_skipped,
    )
    print(
        "Manual review:",
        batch_result.jobs_manual_review,
    )

    for index, item in enumerate(
        batch_result.results,
        start=1,
    ):
        print(
            f"Job {index}: "
            f"{item.external_job_id} | "
            f"{item.match_result.overall_score:.0%} | "
            f"{item.eligibility_decision.value} | "
            f"queued={item.queued}"
        )

    print()
    print("=" * 70)
    print("APPLICATION PIPELINE SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
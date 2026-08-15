"""
JOB MATCHING SERVICE VERIFICATION TEST

Tests the pure domain/service matching engine.

This test does NOT require:
- PostgreSQL
- Supabase
- Playwright
- LinkedIn
- Alembic

It verifies:
1. Strong matching job
2. Missing required skill
3. Excluded company
4. Excluded role
5. Low-score job
6. Remote preference
7. Location preference
8. Experience matching
9. Batch matching
10. Score calculation and decision logic
"""

from __future__ import annotations

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.domain.matching.job_matching import (
    CandidateJobProfile,
)
from src.modules.job_discovery.services.matching.job_matching_service import (
    JobMatchingService,
)
from src.shared.config.constants import (
    EmploymentType,
    JobSourceType,
    RemoteStatus,
)


def print_result(
    number: int,
    name: str,
    result,
) -> None:
    print()
    print("=" * 70)
    print(f"[{number}/10] {name}")
    print("=" * 70)

    print(f"External Job ID : {result.external_job_id}")
    print(f"Decision        : {result.decision}")
    print(f"Overall Score   : {result.overall_score:.0%}")
    print(f"Reason          : {result.reason}")

    print()
    print("BREAKDOWN")
    print(f"Title           : {result.breakdown.title_score:.0%}")
    print(f"Skills          : {result.breakdown.skill_score:.0%}")
    print(f"Location        : {result.breakdown.location_score:.0%}")
    print(f"Remote          : {result.breakdown.remote_score:.0%}")
    print(f"Experience      : {result.breakdown.experience_score:.0%}")

    print()
    print(
        "Matched Skills  : "
        f"{result.breakdown.matched_skills}"
    )

    print(
        "Missing Skills  : "
        f"{result.breakdown.missing_required_skills}"
    )

    print(
        "Matched Roles   : "
        f"{result.breakdown.matched_roles}"
    )

    print(
        "Exclusions      : "
        f"{result.breakdown.excluded_reasons}"
    )


def main() -> None:
    print()
    print("=" * 70)
    print("JOB MATCHING SERVICE VERIFICATION TEST")
    print("=" * 70)

    service = JobMatchingService()

    # ------------------------------------------------------------------
    # Candidate profile
    # ------------------------------------------------------------------

    profile = CandidateJobProfile(
        target_roles=(
            "Data Analyst",
            "Business Analyst",
        ),
        preferred_locations=(
            "Hyderabad",
            "Bangalore",
        ),
        preferred_remote_statuses=(
            "remote",
            "hybrid",
        ),
        required_skills=(
            "SQL",
            "Excel",
            "Python",
        ),
        preferred_skills=(
            "Power BI",
            "JIRA",
        ),
        excluded_roles=(
            "Sales Manager",
            "Telecaller",
        ),
        excluded_companies=(
            "Bad Company",
        ),
        minimum_experience_years=2.0,
        maximum_experience_years=4.0,
        minimum_match_score=0.70,
    )

    # ------------------------------------------------------------------
    # [1] Strong match
    # ------------------------------------------------------------------

    strong_job = DiscoveredJob(
        external_id="matching-test-strong",
        title="Senior Data Analyst",
        company_name="AI Analytics Company",
        source=JobSourceType.LINKEDIN,
        url="https://example.com/jobs/strong",
        location="Hyderabad - Hybrid",
        remote_status=RemoteStatus.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "We are looking for a Data Analyst with 2 years "
            "of experience. Strong SQL, Excel, Python and "
            "Power BI skills are required."
        ),
    )

    strong_result = service.match(
        strong_job,
        profile,
    )

    print_result(
        1,
        "Testing strong Data Analyst match",
        strong_result,
    )

    assert strong_result.decision == "apply"
    assert strong_result.overall_score >= 0.70
    assert strong_result.breakdown.title_score > 0
    assert strong_result.breakdown.skill_score > 0
    assert strong_result.breakdown.location_score == 1.0
    assert strong_result.breakdown.remote_score == 1.0

    print("STRONG MATCH successful")

    # ------------------------------------------------------------------
    # [2] Missing required skill
    # ------------------------------------------------------------------

    missing_skill_job = DiscoveredJob(
        external_id="matching-test-missing-skill",
        title="Data Analyst",
        company_name="Analytics Company",
        source=JobSourceType.LINKEDIN,
        url="https://example.com/jobs/missing-skill",
        location="Hyderabad",
        remote_status=RemoteStatus.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "Data Analyst required with SQL and Excel. "
            "Power BI experience is preferred."
        ),
    )

    missing_skill_result = service.match(
        missing_skill_job,
        profile,
    )

    print_result(
        2,
        "Testing missing required skill handling",
        missing_skill_result,
    )

    assert (
        "python"
        in missing_skill_result.breakdown.missing_required_skills
    )

    assert missing_skill_result.decision in {
        "manual_review",
        "skip",
    }

    print("MISSING REQUIRED SKILL handling successful")

    # ------------------------------------------------------------------
    # [3] Excluded company
    # ------------------------------------------------------------------

    excluded_company_job = DiscoveredJob(
        external_id="matching-test-excluded-company",
        title="Data Analyst",
        company_name="Bad Company",
        source=JobSourceType.LINKEDIN,
        url="https://example.com/jobs/excluded-company",
        location="Hyderabad",
        remote_status=RemoteStatus.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "Data Analyst with SQL, Excel and Python."
        ),
    )

    excluded_company_result = service.match(
        excluded_company_job,
        profile,
    )

    print_result(
        3,
        "Testing excluded company",
        excluded_company_result,
    )

    assert excluded_company_result.decision == "skip"

    assert any(
        "Excluded company" in reason
        for reason in (
            excluded_company_result
            .breakdown
            .excluded_reasons
        )
    )

    print("EXCLUDED COMPANY handling successful")

    # ------------------------------------------------------------------
    # [4] Excluded role
    # ------------------------------------------------------------------

    excluded_role_job = DiscoveredJob(
        external_id="matching-test-excluded-role",
        title="Sales Manager",
        company_name="Good Company",
        source=JobSourceType.LINKEDIN,
        url="https://example.com/jobs/excluded-role",
        location="Hyderabad",
        remote_status=RemoteStatus.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "Sales Manager responsible for sales targets."
        ),
    )

    excluded_role_result = service.match(
        excluded_role_job,
        profile,
    )

    print_result(
        4,
        "Testing excluded role",
        excluded_role_result,
    )

    assert excluded_role_result.decision == "skip"

    assert any(
        "Excluded role" in reason
        for reason in (
            excluded_role_result
            .breakdown
            .excluded_reasons
        )
    )

    print("EXCLUDED ROLE handling successful")

    # ------------------------------------------------------------------
    # [5] Low-score job
    # ------------------------------------------------------------------

    low_score_job = DiscoveredJob(
        external_id="matching-test-low-score",
        title="Graphic Designer",
        company_name="Design Company",
        source=JobSourceType.INDEED,
        url="https://example.com/jobs/low-score",
        location="Mumbai",
        remote_status=RemoteStatus.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "Graphic designer required. "
            "Adobe Photoshop and Illustrator experience."
        ),
    )

    low_score_result = service.match(
        low_score_job,
        profile,
    )

    print_result(
        5,
        "Testing low-score unrelated job",
        low_score_result,
    )

    assert low_score_result.decision == "skip"
    assert low_score_result.overall_score < 0.70

    print("LOW SCORE handling successful")

    # ------------------------------------------------------------------
    # [6] Remote preference
    # ------------------------------------------------------------------

    remote_job = DiscoveredJob(
        external_id="matching-test-remote",
        title="Business Analyst",
        company_name="Remote Analytics Company",
        source=JobSourceType.LINKEDIN,
        url="https://example.com/jobs/remote",
        location="Remote - India",
        remote_status=RemoteStatus.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "Business Analyst with 3 years of experience. "
            "SQL, Excel and Python skills required."
        ),
    )

    remote_result = service.match(
        remote_job,
        profile,
    )

    print_result(
        6,
        "Testing remote preference",
        remote_result,
    )

    assert remote_result.breakdown.remote_score == 1.0

    print("REMOTE preference handling successful")

    # ------------------------------------------------------------------
    # [7] Location preference
    # ------------------------------------------------------------------

    location_job = DiscoveredJob(
        external_id="matching-test-location",
        title="Business Analyst",
        company_name="Location Analytics Company",
        source=JobSourceType.NAUKRI,
        url="https://example.com/jobs/location",
        location="Bangalore, Karnataka",
        remote_status=RemoteStatus.ONSITE,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "Business Analyst with 3 years of experience. "
            "SQL, Excel and Python."
        ),
    )

    location_result = service.match(
        location_job,
        profile,
    )

    print_result(
        7,
        "Testing preferred location",
        location_result,
    )

    assert location_result.breakdown.location_score == 1.0

    print("LOCATION preference handling successful")

    # ------------------------------------------------------------------
    # [8] Experience matching
    # ------------------------------------------------------------------

    experience_job = DiscoveredJob(
        external_id="matching-test-experience",
        title="Data Analyst",
        company_name="Experience Analytics Company",
        source=JobSourceType.LINKEDIN,
        url="https://example.com/jobs/experience",
        location="Hyderabad",
        remote_status=RemoteStatus.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        description=(
            "Data Analyst position requiring 3 years "
            "of experience with SQL and Excel."
        ),
    )

    experience_result = service.match(
        experience_job,
        profile,
    )

    print_result(
        8,
        "Testing experience matching",
        experience_result,
    )

    assert experience_result.breakdown.experience_score == 1.0

    print("EXPERIENCE matching successful")

    # ------------------------------------------------------------------
    # [9] Batch matching
    # ------------------------------------------------------------------

    batch_jobs = (
        strong_job,
        remote_job,
        location_job,
        low_score_job,
    )

    batch_results = service.match_many(
        batch_jobs,
        profile,
    )

    print()
    print("=" * 70)
    print("[9/10] Testing batch matching")
    print("=" * 70)

    print(
        f"Jobs supplied   : {len(batch_jobs)}"
    )

    print(
        f"Results returned : {len(batch_results)}"
    )

    assert len(batch_results) == len(batch_jobs)

    for result in batch_results:
        print(
            f"- {result.external_job_id}: "
            f"{result.decision} "
            f"({result.overall_score:.0%})"
        )

    print("BATCH matching successful")

    # ------------------------------------------------------------------
    # [10] Score and decision validation
    # ------------------------------------------------------------------

    print()
    print("=" * 70)
    print("[10/10] Verifying scoring and decision logic")
    print("=" * 70)

    print(
        f"Title weight       : "
        f"{service.TITLE_WEIGHT:.0%}"
    )

    print(
        f"Skill weight       : "
        f"{service.SKILL_WEIGHT:.0%}"
    )

    print(
        f"Location weight    : "
        f"{service.LOCATION_WEIGHT:.0%}"
    )

    print(
        f"Remote weight      : "
        f"{service.REMOTE_WEIGHT:.0%}"
    )

    print(
        f"Experience weight  : "
        f"{service.EXPERIENCE_WEIGHT:.0%}"
    )

    total_weight = (
        service.TITLE_WEIGHT
        + service.SKILL_WEIGHT
        + service.LOCATION_WEIGHT
        + service.REMOTE_WEIGHT
        + service.EXPERIENCE_WEIGHT
    )

    print(
        f"Total weight       : "
        f"{total_weight:.0%}"
    )

    assert abs(total_weight - 1.0) < 0.0001

    valid_decisions = {
        "apply",
        "skip",
        "manual_review",
    }

    for result in batch_results:
        assert result.decision in valid_decisions
        assert 0.0 <= result.overall_score <= 1.0

    print("WEIGHT validation successful")
    print("DECISION validation successful")
    print("SCORE range validation successful")

    print()
    print("=" * 70)
    print("JOB MATCHING SERVICE VERIFICATION PASSED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
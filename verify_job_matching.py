"""
JOB MATCHING SERVICE INTEGRATION TEST

Verifies:
    1. Candidate profile creation
    2. Matching service creation
    3. Strong Data Analyst match
    4. Business Data Analyst role variation
    5. Skill matching
    6. Location matching
    7. Excluded role handling
    8. Excluded company handling
    9. Manual-review decision
    10. Multiple-job matching
"""

from __future__ import annotations

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.domain.matching import (
    CandidateJobProfile,
)
from src.modules.job_discovery.services.matching import (
    JobMatchingService,
)
from src.shared.config.constants import (
    DecisionType,
    JobSourceType,
    RemoteStatus,
)


def print_result(
    label: str,
    result,
) -> None:
    print(f"\n{label}")
    print("-" * 70)
    print(f"External ID: {result.external_job_id}")
    print(f"Overall score: {result.overall_score:.0%}")
    print(f"Decision: {result.decision}")
    print(f"Reason: {result.reason}")
    print(
        f"Title score: "
        f"{result.breakdown.title_score:.0%}"
    )
    print(
        f"Skill score: "
        f"{result.breakdown.skill_score:.0%}"
    )
    print(
        f"Location score: "
        f"{result.breakdown.location_score:.0%}"
    )
    print(
        f"Remote score: "
        f"{result.breakdown.remote_score:.0%}"
    )
    print(
        f"Experience score: "
        f"{result.breakdown.experience_score:.0%}"
    )
    print(
        f"Matched roles: "
        f"{result.breakdown.matched_roles}"
    )
    print(
        f"Matched skills: "
        f"{result.breakdown.matched_skills}"
    )
    print(
        f"Missing required skills: "
        f"{result.breakdown.missing_required_skills}"
    )


def main() -> None:
    print("=" * 70)
    print("JOB MATCHING SERVICE INTEGRATION TEST")
    print("=" * 70)

    # ---------------------------------------------------------------
    # 1/10 Candidate profile
    # ---------------------------------------------------------------

    print("\n[1/10] Creating candidate job profile...")

    profile = CandidateJobProfile(
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
            "onsite",
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
        minimum_experience_years=2.0,
        maximum_experience_years=5.0,
        minimum_match_score=0.70,
    )

    print("CANDIDATE PROFILE successful")
    print(
        "Target roles:",
        profile.target_roles,
    )
    print(
        "Preferred locations:",
        profile.preferred_locations,
    )
    print(
        "Required skills:",
        profile.required_skills,
    )
    print(
        "Preferred skills:",
        profile.preferred_skills,
    )
    print(
        "Minimum match score:",
        f"{profile.minimum_match_score:.0%}",
    )

    # ---------------------------------------------------------------
    # 2/10 Service creation
    # ---------------------------------------------------------------

    print("\n[2/10] Creating matching service...")

    service = JobMatchingService()

    assert isinstance(
        service,
        JobMatchingService,
    )

    print("MATCHING SERVICE creation successful")

    # ---------------------------------------------------------------
    # 3/10 Strong Data Analyst match
    # ---------------------------------------------------------------

    print(
        "\n[3/10] Testing strong Data Analyst match..."
    )

    data_analyst_job = DiscoveredJob(
        external_id="match-test-001",
        title="Data Analyst",
        company_name="Analytics Corporation",
        source=JobSourceType.LINKEDIN,
        url="https://www.linkedin.com/jobs/view/match-test-001",
        location="Hyderabad, Telangana, India",
        remote_status=RemoteStatus.HYBRID,
        description=(
            "We are looking for a Data Analyst with "
            "2+ years of experience. "
            "Strong SQL and Excel skills are required. "
            "Power BI and Python are preferred. "
            "Responsibilities include data analysis, "
            "reporting and dashboard development."
        ),
    )

    result = service.match(
        data_analyst_job,
        profile,
    )

    print_result(
        "DATA ANALYST MATCH",
        result,
    )

    assert result.decision == DecisionType.APPLY.value
    assert result.overall_score >= 0.70

    print("STRONG MATCH successful")

    # ---------------------------------------------------------------
    # 4/10 Role variation
    # ---------------------------------------------------------------

    print(
        "\n[4/10] Testing role-name variation..."
    )

    business_data_job = DiscoveredJob(
        external_id="match-test-002",
        title="Business Data Analyst",
        company_name="Example Technologies",
        source=JobSourceType.LINKEDIN,
        url="https://www.linkedin.com/jobs/view/match-test-002",
        location="Hyderabad, Telangana, India",
        remote_status=RemoteStatus.REMOTE,
        description=(
            "Business Data Analyst responsible for "
            "SQL reporting, Excel analysis, Power BI "
            "dashboards and Python-based data processing. "
            "Requires 2 years of experience."
        ),
    )

    variation_result = service.match(
        business_data_job,
        profile,
    )

    print_result(
        "BUSINESS DATA ANALYST MATCH",
        variation_result,
    )

    assert (
        variation_result.breakdown.title_score
        >= 0.70
    )

    print("ROLE VARIATION successful")

    # ---------------------------------------------------------------
    # 5/10 Skill matching
    # ---------------------------------------------------------------

    print("\n[5/10] Testing skill matching...")

    assert (
        "sql"
        in variation_result.breakdown.matched_skills
    )

    assert (
        "excel"
        in variation_result.breakdown.matched_skills
    )

    print("SKILL MATCHING successful")
    print(
        "Matched skills:",
        variation_result.breakdown.matched_skills,
    )

    # ---------------------------------------------------------------
    # 6/10 Location matching
    # ---------------------------------------------------------------

    print(
        "\n[6/10] Testing location matching..."
    )

    assert (
        variation_result.breakdown.location_score
        == 1.0
    )

    assert (
        variation_result.breakdown.remote_score
        == 1.0
    )

    print("LOCATION MATCHING successful")
    print(
        "Location score:",
        f"{variation_result.breakdown.location_score:.0%}",
    )
    print(
        "Remote score:",
        f"{variation_result.breakdown.remote_score:.0%}",
    )

    # ---------------------------------------------------------------
    # 7/10 Excluded role
    # ---------------------------------------------------------------

    print("\n[7/10] Testing excluded role...")

    excluded_role_job = DiscoveredJob(
        external_id="match-test-003",
        title="Senior Data Scientist",
        company_name="Analytics Corporation",
        source=JobSourceType.LINKEDIN,
        url="https://www.linkedin.com/jobs/view/match-test-003",
        location="Hyderabad",
        remote_status=RemoteStatus.HYBRID,
        description=(
            "Senior Data Scientist with SQL, Excel, "
            "Python and machine learning experience."
        ),
    )

    excluded_role_result = service.match(
        excluded_role_job,
        profile,
    )

    print_result(
        "EXCLUDED ROLE",
        excluded_role_result,
    )

    assert (
        excluded_role_result.decision
        == DecisionType.SKIP.value
    )

    assert excluded_role_result.breakdown.excluded_reasons

    print("EXCLUDED ROLE handling successful")

    # ---------------------------------------------------------------
    # 8/10 Excluded company
    # ---------------------------------------------------------------

    print(
        "\n[8/10] Testing excluded company..."
    )

    excluded_company_job = DiscoveredJob(
        external_id="match-test-004",
        title="Data Analyst",
        company_name="Excluded Test Company",
        source=JobSourceType.LINKEDIN,
        url="https://www.linkedin.com/jobs/view/match-test-004",
        location="Hyderabad",
        remote_status=RemoteStatus.ONSITE,
        description=(
            "Data Analyst with 2 years of experience "
            "using SQL and Excel."
        ),
    )

    excluded_company_result = service.match(
        excluded_company_job,
        profile,
    )

    print_result(
        "EXCLUDED COMPANY",
        excluded_company_result,
    )

    assert (
        excluded_company_result.decision
        == DecisionType.SKIP.value
    )

    print(
        "EXCLUDED COMPANY handling successful"
    )

    # ---------------------------------------------------------------
    # 9/10 Manual review
    # ---------------------------------------------------------------

    print(
        "\n[9/10] Testing manual-review decision..."
    )

    review_job = DiscoveredJob(
        external_id="match-test-005",
        title="Business Systems Analyst",
        company_name="Review Corporation",
        source=JobSourceType.LINKEDIN,
        url="https://www.linkedin.com/jobs/view/match-test-005",
        location="Hyderabad",
        remote_status=RemoteStatus.HYBRID,
        description=(
            "Business Systems Analyst responsible "
            "for business reporting and stakeholder "
            "requirements."
        ),
    )

    review_result = service.match(
        review_job,
        profile,
    )

    print_result(
        "MANUAL REVIEW",
        review_result,
    )

    assert (
    review_result.decision
    == DecisionType.MANUAL_REVIEW.value
    )

    print(
        "MANUAL REVIEW decision path successful"
    )

    # ---------------------------------------------------------------
    # 10/10 Multiple-job matching
    # ---------------------------------------------------------------

    print(
        "\n[10/10] Testing multiple-job matching..."
    )

    jobs = (
        data_analyst_job,
        business_data_job,
        excluded_role_job,
        excluded_company_job,
        review_job,
    )

    results = service.match_many(
        jobs,
        profile,
    )

    assert len(results) == len(jobs)

    print("MULTIPLE JOB MATCHING successful")
    print(
        "Jobs evaluated:",
        len(results),
    )

    for index, match_result in enumerate(
        results,
        start=1,
    ):
        print(
            f"Job {index}: "
            f"{match_result.external_job_id} | "
            f"{match_result.overall_score:.0%} | "
            f"{match_result.decision}"
        )

    print("\n" + "=" * 70)
    print("JOB MATCHING SERVICE INTEGRATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
from src.modules.job_discovery.domain.matching.job_matching import (
    CandidateJobProfile,
)
from src.modules.job_discovery.infrastructure.repositories.job.job_repository_impl import (
    SQLAlchemyJobRepository,
)
from src.modules.job_discovery.services.matching.job_matching_service import (
    JobMatchingService,
)
from src.shared.config.constants import JobSourceType
from src.shared.database.session import session_scope


profile = CandidateJobProfile(
    target_roles=(
        "Data Analyst",
        "Business Analyst",
    ),
    preferred_locations=(
        "Hyderabad",
        "Bengaluru",
        "Pune",
        "Mumbai",
        "Chennai",
        "Noida",
        "Gurugram",
    ),
    preferred_remote_statuses=(
        "onsite",
        "hybrid",
        "remote",
    ),
    required_skills=(
        "SQL",
        "Python",
        "Power BI",
    ),
    preferred_skills=(
        "Tableau",
        "Excel",
        "Jira",
        "ETL",
        "Data Visualization",
        "Data Cleaning",
        "Data Preparation",
        "Data Wrangling",
        "Statistical Analysis",
        "Data Interpretation",
        "DBMS",
        "GitHub",
        "GitLab",
        "PowerShell",
        "MySQL Workbench",
        "Stored Procedures",
        "Data Storytelling",
        "Business Acumen",
        "Data Management",
        "Data Extraction",
        "GenAI",
        "Prompt Engineering",
        "NLP",
        "AI Concepts",
        "Critical Thinking",
        "Problem Solving",
        "Teamwork",
        "Attention to Detail",
    ),
    minimum_experience_years=0,
    maximum_experience_years=3,
    minimum_match_score=0.50,
)


service = JobMatchingService()


print("=" * 60)
print("JOB MATCHING TEST")
print("=" * 60)


with session_scope() as db:

    repository = SQLAlchemyJobRepository(db)

    job = repository.get_by_external_id(
        source=JobSourceType.LINKEDIN,
        external_job_id="test-data-analyst-001",
    )

    if job is None:
        print("TEST JOB NOT FOUND")
        raise SystemExit(1)

    print(f"JOB: {job.title}")
    print(f"COMPANY: {job.company_name}")
    print(f"LOCATION: {job.location}")
    print(f"SOURCE: {job.source}")

    print()
    print("--- DOMAIN OBJECT ---")
    print(f"TYPE: {type(job).__name__}")
    print(f"REMOTE STATUS: {job.remote_status}")
    print(f"EMPLOYMENT TYPE: {job.employment_type}")

    result = service.match(
        job,
        profile,
    )

    print()
    print("--- MATCH RESULT ---")
    print(f"SCORE: {result.overall_score}")
    print(f"DECISION: {result.decision}")
    print(f"REASON: {result.reason}")

    print()
    print("--- ROLE ---")
    print(
        f"ROLE FAMILY: "
        f"{result.metadata.get('role_family')}"
    )

    print(
        f"ROLE PRIORITY: "
        f"{result.metadata.get('role_priority')}"
    )

    print(
        f"MATCHED ROLES: "
        f"{result.breakdown.matched_roles}"
    )

    print()
    print("--- SKILLS ---")
    print(
        f"MATCHED: "
        f"{result.breakdown.matched_skills}"
    )

    print(
        f"MISSING REQUIRED: "
        f"{result.breakdown.missing_required_skills}"
    )

    print()
    print("--- SCORE BREAKDOWN ---")
    print(
        f"TITLE: "
        f"{result.breakdown.title_score}"
    )

    print(
        f"SKILLS: "
        f"{result.breakdown.skill_score}"
    )

    print(
        f"LOCATION: "
        f"{result.breakdown.location_score}"
    )

    print(
        f"WORK MODE: "
        f"{result.breakdown.remote_score}"
    )

    print(
        f"EXPERIENCE: "
        f"{result.breakdown.experience_score}"
    )

    print()
    print("--- EXCLUSIONS ---")
    print(
        f"EXCLUDED REASONS: "
        f"{result.breakdown.excluded_reasons}"
    )

    print()
    print("--- AUTOMATION ---")

    print(
        "AUTOMATIC APPLICATION ELIGIBLE: "
        f"{result.metadata.get('automatic_application_eligible')}"
    )

    print(
        "MINIMUM MATCH SCORE: "
        f"{profile.minimum_match_score}"
    )

    print(
        "ACTUAL MATCH SCORE: "
        f"{result.overall_score}"
    )

    print(
        "THRESHOLD PASSED: "
        f"{result.overall_score >= profile.minimum_match_score}"
    )

    print()
    print("--- METADATA ---")

    for key, value in result.metadata.items():
        print(f"{key}: {value}")


print()
print("=" * 60)
print("TEST COMPLETED")
print("=" * 60)
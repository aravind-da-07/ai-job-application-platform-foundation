"""
End-to-end application question mapping and answer resolution test.

Pipeline:

Realistic application question
        ↓
LinkedInApplicationFieldMapper
        ↓
Normalized application field
        ↓
AnswerResolverService
        ↓
Resolved answer
"""

from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.mapping.field_mapper import (
    LinkedInApplicationFieldMapper,
)
from src.modules.job_discovery.services.application_executor.answers.answer_resolver_service import (
    AnswerResolverService,
)
from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswerDecision,
)
from src.modules.job_discovery.domain.application_executor.form import (
    ApplicationFormField,
)


# ------------------------------------------------------------------
# Candidate data
# ------------------------------------------------------------------

candidate_data = {
    "full_name": "Aravind Reddy",
    "email": "aravind@example.com",
    "phone": "9999999999",
    "location": "Hyderabad",

    "experience_years": 2.8333,

    "skills": [
        "SQL",
        "Python",
        "Power BI",
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
    ],

    "certifications": [
        "Business Analyst Certification",
        "Python Essentials 1",
    ],

    "salary": "₹7–9 LPA",

    "notice_period": "0 days",

    "immediate_joiner": True,

    "joining_date": "2026-08-31",

    "target_role": (
        "Data Analyst",
        "Business Analyst",
    ),

    "preferred_location": (
        "Hyderabad",
        "Bengaluru",
        "Pune",
        "Mumbai",
        "Chennai",
        "Noida",
        "Gurugram",
    ),

    "work_mode": (
        "onsite",
        "hybrid",
        "remote",
    ),
}


# ------------------------------------------------------------------
# Realistic application questions
# ------------------------------------------------------------------

questions = (
    "Do you have experience with SQL?",
    "Do you have experience with Python?",
    "Are you proficient in Power BI?",
    "Do you have Tableau experience?",
    "Are you proficient in Microsoft Excel?",
    "How many years of professional experience do you have?",
    "What is your expected salary?",
    "What is your current notice period?",
    "Are you available to join immediately?",
    "What is your earliest joining date?",
    "What is your preferred job role?",
    "What is your preferred work location?",
    "Are you open to onsite, hybrid, or remote work?",
    "Do you have experience with ETL?",
    "Do you have experience with data visualization?",
    "Do you have experience with SQL and stored procedures?",
    "Do you have experience with GitHub?",
    "Do you have experience with GitLab?",
    "Do you have experience with GenAI?",
    "Do you have experience with prompt engineering?",
    "Do you have experience with NLP?",
    "Do you have experience with data cleaning?",
    "Do you have experience with statistical analysis?",
    "Do you have experience with data wrangling?",
    "Do you have experience with PowerShell?",
    "Do you have experience with MySQL Workbench?",
    "Do you have experience with Jira?",
    "Do you have experience with business intelligence?",
    "Do you have experience with a technology not listed in your profile?",
)


# ------------------------------------------------------------------
# Create form fields
# ------------------------------------------------------------------

application_fields = tuple(
    ApplicationFormField(
        field_id=f"linkedin_question_{index}",
        label=question,
        field_type="text",
        required=False,
    )
    for index, question in enumerate(
        questions,
        start=1,
    )
)


# ------------------------------------------------------------------
# Initialize components
# ------------------------------------------------------------------

mapper = LinkedInApplicationFieldMapper()

resolver = AnswerResolverService()


print("=" * 80)
print("APPLICATION QUESTION MAPPING + ANSWER RESOLUTION TEST")
print("=" * 80)

print()
print(
    f"TOTAL QUESTIONS: "
    f"{len(application_fields)}"
)


# ------------------------------------------------------------------
# STEP 1 — Mapping
# ------------------------------------------------------------------

mapped_fields = mapper.map_fields(
    application_fields
)


print()
print("=" * 80)
print("STEP 1 — FIELD MAPPING")
print("=" * 80)


for original, mapped in zip(
    application_fields,
    mapped_fields,
):
    print()
    print(
        f"QUESTION: "
        f"{original.label}"
    )

    print(
        f"NORMALIZED: "
        f"{mapped.normalized_name}"
    )

    print(
        f"CONFIDENCE: "
        f"{mapped.confidence}"
    )


# ------------------------------------------------------------------
# STEP 2 — Answer resolution
# ------------------------------------------------------------------

resolution = resolver.resolve_fields(
    fields=mapped_fields,
    candidate_data=candidate_data,
)


print()
print("=" * 80)
print("STEP 2 — ANSWER RESOLUTION")
print("=" * 80)


for answer in resolution.answers:
    print()
    print(
        f"FIELD: "
        f"{answer.field_id}"
    )

    print(
        f"NORMALIZED: "
        f"{answer.normalized_field_name}"
    )

    print(
        f"VALUE: "
        f"{answer.value}"
    )

    print(
        f"DECISION: "
        f"{answer.decision.value}"
    )

    print(
        f"CONFIDENCE: "
        f"{answer.confidence}"
    )

    print(
        f"REASON: "
        f"{answer.reason}"
    )


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

print()
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

print(
    f"TOTAL QUESTIONS: "
    f"{len(resolution.answers)}"
)

print(
    f"AUTO ANSWERS: "
    f"{resolution.auto_answer_count}"
)

print(
    f"MANUAL REVIEW: "
    f"{resolution.manual_review_count}"
)

print(
    f"SKIPPED: "
    f"{resolution.skipped_count}"
)

print(
    f"AUTOMATIC ANSWER RATE: "
    f"{resolution.metadata.get('automatic_answer_rate')}"
)


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------

print()
print("=" * 80)
print("VALIDATION")
print("=" * 80)


unknown_answers = [
    answer
    for answer in resolution.answers
    if answer.normalized_field_name == "unknown"
]


print(
    f"UNKNOWN QUESTIONS: "
    f"{len(unknown_answers)}"
)


for answer in unknown_answers:
    print(
        f"UNKNOWN FIELD: "
        f"{answer.field_id}"
    )


# At least one unsupported question must remain unknown.
assert any(
    answer.normalized_field_name == "unknown"
    and answer.decision
    == ApplicationAnswerDecision.MANUAL_REVIEW
    for answer in resolution.answers
)


# There must be supported questions.
supported_answers = [
    answer
    for answer in resolution.answers
    if answer.normalized_field_name != "unknown"
]


assert len(supported_answers) > 0


# Automatic answers must contain actual values.
for answer in resolution.answers:

    if (
        answer.decision
        == ApplicationAnswerDecision.AUTO_ANSWER
    ):
        assert answer.value is not None

        assert str(
            answer.value
        ).strip()


print()
print("ALL VALIDATIONS PASSED")

print()
print("=" * 80)
print("TEST COMPLETED")
print("=" * 80)
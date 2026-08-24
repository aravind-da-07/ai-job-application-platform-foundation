from src.modules.job_discovery.domain.application_executor.answers import (
    ApplicationAnswerDecision,
)
from src.modules.job_discovery.services.application_executor.answers.answer_resolver_service import (
    AnswerResolverService,
)


class TestField:
    def __init__(
        self,
        field_id: str,
        normalized_name: str,
    ) -> None:
        self.field_id = field_id
        self.normalized_name = normalized_name


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
}


fields = (
    TestField("q1", "sql_experience"),
    TestField("q2", "python_experience"),
    TestField("q3", "power_bi_experience"),
    TestField("q4", "tableau_experience"),
    TestField("q5", "excel_experience"),
    TestField("q6", "experience_years"),
    TestField("q7", "salary"),
    TestField("q8", "notice_period"),
    TestField("q9", "immediate_joiner"),
    TestField("q10", "unknown"),
)


resolver = AnswerResolverService()

result = resolver.resolve_fields(
    fields=fields,
    candidate_data=candidate_data,
)

print("=" * 70)
print("APPLICATION ANSWER RESOLVER TEST")
print("=" * 70)

for answer in result.answers:
    print()
    print(f"FIELD: {answer.field_id}")
    print(f"NORMALIZED: {answer.normalized_field_name}")
    print(f"VALUE: {answer.value}")
    print(f"DECISION: {answer.decision.value}")
    print(f"CONFIDENCE: {answer.confidence}")
    print(f"REASON: {answer.reason}")

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(
    f"AUTO ANSWERS: "
    f"{result.auto_answer_count}"
)

print(
    f"MANUAL REVIEW: "
    f"{result.manual_review_count}"
)

print(
    f"SKIPPED: "
    f"{result.skipped_count}"
)

print(
    f"AUTOMATIC ANSWER RATE: "
    f"{result.metadata.get('automatic_answer_rate')}"
)

print()

assert result.auto_answer_count == 9
assert result.manual_review_count == 1
assert result.skipped_count == 0

for answer in result.answers:
    if answer.normalized_field_name != "unknown":
        assert (
            answer.decision
            == ApplicationAnswerDecision.AUTO_ANSWER
        )

print("ALL ASSERTIONS PASSED")
print("=" * 70)
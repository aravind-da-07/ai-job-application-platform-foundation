"""
CandidateBuilder tests.

Verifies that extracted resume sections are converted into a
complete Candidate profile.
"""

from __future__ import annotations

from src.modules.resume_intelligence.builders.candidate_builder import (
    CandidateBuilder,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


def test_candidate_builder_builds_complete_candidate() -> None:
    """
    CandidateBuilder should populate all supported candidate sections.
    """

    sections = ExtractedSections(
        header=(
            "Aravind Reddy\n"
            "aravind@example.com\n"
            "+91 9876543210"
        ),
        skills=(
            "Python, SQL, Power BI, Excel, Jira"
        ),
        experience=(
            "Associate Data Analyst at Carelon Global Solutions\n"
            "Hyderabad\n"
            "2024 - Present\n"
            "- Analyzed operational data.\n"
            "- Built reports and dashboards."
        ),
        education=(
            "MBA in Business Analytics\n"
            "Amrita University\n"
            "2024\n"
            "CGPA: 8.0"
        ),
        projects=(
            "Sales Performance Analysis\n"
            "Analyzed sales performance using SQL and Power BI.\n"
            "Technologies: SQL, Power BI, Excel"
        ),
        certifications=(
            "Python Essentials 1\n"
            "Cisco\n"
            "2025\n"
            "Credential ID: PY-001"
        ),
    )

    candidate = CandidateBuilder().build(
        sections
    )

    assert candidate.contact.email == "aravind@example.com"
    assert candidate.contact.phone == "+91 9876543210"

    assert len(candidate.skills) >= 4
    assert any(
        skill.name.casefold() == "python"
        for skill in candidate.skills
    )

    assert len(candidate.experience) == 1
    assert (
        candidate.experience[0].title
        == "Associate Data Analyst"
    )
    assert (
        candidate.experience[0].company
        == "Carelon Global Solutions"
    )
    assert candidate.experience[0].currently_working is True

    assert len(candidate.education) == 1
    assert (
        candidate.education[0].degree
        == "MBA in Business Analytics"
    )
    assert (
        candidate.education[0].institution
        == "Amrita University"
    )

    assert len(candidate.projects) == 1
    assert (
        candidate.projects[0].name
        == "Sales Performance Analysis"
    )

    assert len(candidate.certifications) == 1
    assert (
        candidate.certifications[0].name
        == "Python Essentials 1"
    )
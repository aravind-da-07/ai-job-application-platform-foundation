"""
Resume Section Registry.

Defines the supported resume sections and their common headings.
"""

from __future__ import annotations

SECTION_REGISTRY: dict[str, tuple[str, ...]] = {
    "summary": (
        "summary",
        "professional summary",
        "profile",
        "objective",
        "career objective",
        "about me",
    ),
    "skills": (
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "technical expertise",
    ),
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "career history",
        "work history",
    ),
    "education": (
        "education",
        "academic background",
        "qualifications",
    ),
    "projects": (
        "projects",
        "academic projects",
        "professional projects",
    ),
    "certifications": (
        "certifications",
        "licenses",
        "certificates",
    ),
    "languages": (
        "languages",
    ),
    "achievements": (
        "achievements",
        "awards",
        "accomplishments",
    ),
}
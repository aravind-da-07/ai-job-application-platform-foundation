"""
Resume Section Detector.

Splits parsed resume text into logical sections.
"""

from __future__ import annotations

from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)
from src.modules.resume_intelligence.schemas.resume_parse_result import (
    ResumeParseResult,
)
from src.modules.resume_intelligence.section_detection.section_matcher import (
    SectionMatcher,
)


class SectionDetector:
    """
    Detects logical resume sections from parsed text.
    """

    def detect(
        self,
        parse_result: ResumeParseResult,
    ) -> ExtractedSections:
        """
        Detects and extracts resume sections.
        """

        sections: dict[str, list[str]] = {
            "header": [],
            "summary": [],
            "skills": [],
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "languages": [],
            "achievements": [],
            "other": [],
        }

        current_section = "header"

        for line in parse_result.text.splitlines():

            stripped = line.strip()

            if not stripped:
                continue

            matched = SectionMatcher.match(stripped)

            if matched is not None:
                current_section = matched
                continue

            sections[current_section].append(stripped)

        return ExtractedSections(
            header="\n".join(sections["header"]),
            summary="\n".join(sections["summary"]),
            skills="\n".join(sections["skills"]),
            experience="\n".join(sections["experience"]),
            education="\n".join(sections["education"]),
            projects="\n".join(sections["projects"]),
            certifications="\n".join(sections["certifications"]),
            languages="\n".join(sections["languages"]),
            achievements="\n".join(sections["achievements"]),
            other="\n".join(sections["other"]),
        )
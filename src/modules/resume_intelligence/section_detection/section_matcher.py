"""
Resume Section Matcher.

Matches resume headings to their canonical section names.
"""

from __future__ import annotations

from src.modules.resume_intelligence.section_detection.section_registry import (
    SECTION_REGISTRY,
)


class SectionMatcher:
    """
    Matches resume section headings to canonical section names.
    """

    @staticmethod
    def match(heading: str) -> str | None:
        """
        Returns the canonical section name for a heading.

        Returns None if no match is found.
        """

        normalized = heading.strip().lower()

        for section, headings in SECTION_REGISTRY.items():
            if normalized in headings:
                return section

        return None
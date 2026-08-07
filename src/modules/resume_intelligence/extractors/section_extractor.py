"""
Skills Extractor.

Extracts candidate skills from resume sections.
"""

from __future__ import annotations

from src.modules.resume_intelligence.domain.value_objects.skill import Skill
from src.modules.resume_intelligence.extractors.base_extractor import BaseExtractor
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class SkillsExtractor(BaseExtractor[ExtractedSections, list[Skill]]):
    """
    Extracts skills from the resume.
    """

    def extract(
        self,
        data: ExtractedSections,
    ) -> list[Skill]:
        """
        Extract skills from the skills section.

        Temporary implementation.
        """

        return []


__all__ = ["SkillsExtractor"]
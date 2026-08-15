"""
Skills Extractor.

Extracts normalized candidate skills from the detected skills section.
"""

from __future__ import annotations

import re

from src.modules.resume_intelligence.domain.value_objects.skill import Skill
from src.modules.resume_intelligence.extractors.base_extractor import (
    BaseExtractor,
)
from src.modules.resume_intelligence.schemas.extracted_sections import (
    ExtractedSections,
)


class SkillsExtractor(
    BaseExtractor[ExtractedSections, list[Skill]]
):
    """
    Extracts skills from the resume skills section.

    The extractor intentionally uses deterministic parsing here.
    Semantic normalization and job-specific skill matching belong
    to the AI/ML matching layer.
    """

    _CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
        "programming": (
            "python",
            "java",
            "javascript",
            "typescript",
            "c",
            "c++",
            "c#",
            "r",
            "sql",
        ),
        "data": (
            "sql",
            "mysql",
            "postgresql",
            "excel",
            "power bi",
            "tableau",
            "pandas",
            "numpy",
            "statistics",
            "data analysis",
            "data visualization",
        ),
        "cloud": (
            "aws",
            "azure",
            "gcp",
            "google cloud",
        ),
        "database": (
            "mysql",
            "postgresql",
            "oracle",
            "mongodb",
            "sql server",
            "database",
        ),
        "tools": (
            "git",
            "github",
            "jira",
            "docker",
            "kubernetes",
            "visual studio code",
            "vscode",
        ),
        "business": (
            "business analysis",
            "business analyst",
            "requirements gathering",
            "process improvement",
            "stakeholder management",
            "mis reporting",
        ),
    }

    _SEPARATORS = re.compile(
        r"[,\n;|•●▪◦]+"
    )

    def extract(
        self,
        data: ExtractedSections,
    ) -> list[Skill]:
        """
        Extract skills from the skills section.

        Supports common resume formats such as:

            Python, SQL, Power BI

        and:

            Python
            SQL
            Power BI

        and bullet-separated skill lists.
        """

        text = data.skills.strip()

        if not text:
            return []

        candidates = self._SEPARATORS.split(text)

        skills: list[Skill] = []
        seen: set[str] = set()

        for candidate in candidates:
            normalized = self._normalize_skill(candidate)

            if not normalized:
                continue

            key = normalized.casefold()

            if key in seen:
                continue

            seen.add(key)

            skills.append(
                Skill(
                    name=normalized,
                    category=self._categorize(normalized),
                )
            )

        return skills

    @staticmethod
    def _normalize_skill(value: str) -> str:
        """
        Normalize a raw skill without destroying meaningful symbols.
        """

        value = re.sub(
            r"^[\s\-–—:]+|[\s\-–—:]+$",
            "",
            value.strip(),
        )

        value = re.sub(
            r"^\s*(?:skills?|technical skills?)\s*:\s*",
            "",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        if not value:
            return ""

        # Ignore obvious prose fragments.
        if len(value) > 80:
            return ""

        return value

    @classmethod
    def _categorize(
        cls,
        skill_name: str,
    ) -> str | None:
        """
        Assign a broad category when the skill is recognized.
        """

        normalized = skill_name.casefold()

        for category, keywords in cls._CATEGORY_KEYWORDS.items():
            if normalized in keywords:
                return category

        return None


__all__ = ["SkillsExtractor"]
"""
Skills Service.

Provides business logic for extracting and matching skills.
"""

from __future__ import annotations

from src.modules.resume_intelligence.domain.value_objects.skill import Skill
from src.modules.resume_intelligence.repositories import SkillsRepository


class SkillsService:
    """
    Business service responsible for skill matching.
    """

    def __init__(self) -> None:
        self._repository = SkillsRepository()

    def extract_skills(
        self,
        text: str,
    ) -> list[Skill]:
        """
        Extracts matching skills from supplied text.
        """

        normalized_text = text.lower()

        matched: dict[str, Skill] = {}

        for skill in self._repository.get_all_skills():

            if skill.name.lower() in normalized_text:
                matched[skill.name.lower()] = skill

        return sorted(
            matched.values(),
            key=lambda skill: skill.name,
        )

    def contains(
        self,
        skill_name: str,
    ) -> bool:
        """
        Returns True if the supplied skill exists in the repository.
        """

        return self._repository.exists(skill_name)

    def available_categories(
        self,
    ) -> tuple[str, ...]:
        """
        Returns supported skill categories.
        """

        return self._repository.categories()


__all__ = [
    "SkillsService",
]
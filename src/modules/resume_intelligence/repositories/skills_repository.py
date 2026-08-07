"""
Skills Repository.

Provides access to normalized skills stored under the Resume Intelligence
assets directory.
"""

from __future__ import annotations

from collections.abc import Iterable

from src.modules.resume_intelligence.domain.value_objects.skill import Skill
from src.modules.resume_intelligence.utils.asset_loader import AssetLoader


class SkillsRepository:
    """
    Repository responsible for loading and providing skills.

    Skills are currently loaded from text assets.

    Future versions can replace the implementation with Supabase or
    another persistent store without affecting consumers.
    """

    def __init__(self) -> None:
        self._loader = AssetLoader()

        self._cache: dict[str, list[Skill]] = {}

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def get_skills(
        self,
        category: str,
    ) -> list[Skill]:
        """
        Returns all skills for a category.

        Example:
            repository.get_skills("programming")
        """

        category = category.strip().lower()

        if category in self._cache:
            return self._cache[category]

        file_name = f"skills/{category}.txt"

        lines = self._loader.read_lines(file_name)

        skills = [
            Skill(
                name=line,
                category=category,
            )
            for line in lines
        ]

        self._cache[category] = skills

        return skills

    def get_all_skills(self) -> list[Skill]:
        """
        Returns every available skill across all categories.
        """

        categories = (
            "analytics",
            "cloud",
            "databases",
            "healthcare",
            "programming",
            "tools",
        )

        all_skills: list[Skill] = []

        for category in categories:
            all_skills.extend(
                self.get_skills(category)
            )

        return all_skills

    def get_skill_names(self) -> set[str]:
        """
        Returns every skill as normalized lowercase text.

        Useful for fast matching.
        """

        return {
            skill.name.lower()
            for skill in self.get_all_skills()
        }

    def exists(
        self,
        skill_name: str,
    ) -> bool:
        """
        Returns True if the supplied skill exists.
        """

        return (
            skill_name.strip().lower()
            in self.get_skill_names()
        )

    def categories(self) -> tuple[str, ...]:
        """
        Returns supported skill categories.
        """

        return (
            "analytics",
            "cloud",
            "databases",
            "healthcare",
            "programming",
            "tools",
        )

    def clear_cache(self) -> None:
        """
        Clears the in-memory cache.
        """

        self._cache.clear()


__all__ = ["SkillsRepository"]
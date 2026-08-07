"""
Skill Value Object.

Represents a single normalized skill extracted from a resume.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Skill(BaseModel):
    """
    Immutable value object representing a candidate skill.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    name: str = Field(
        description="Normalized skill name."
    )

    category: str |None = Field(
        default=None,
        description="Skill category."
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """
        Normalize the skill name.
        """
        value = value.strip()

        if not value:
            raise ValueError("Skill name cannot be empty.")

        return value

    @field_validator("category")
    @classmethod
    def validate_category(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Normalize the skill category.
        """

        if value is None:
            return None

        value = value.strip()

        return value or None


__all__ = ["Skill"]
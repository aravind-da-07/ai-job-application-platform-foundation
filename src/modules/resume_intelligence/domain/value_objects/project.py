"""
Project Value Object.

Represents a candidate project.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Project(BaseModel):
    """
    Immutable project value object.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    name: str = Field(
        default="",
        description="Project name.",
    )

    description: str | None = Field(
        default=None,
        description="Project description.",
    )

    technologies: list[str] = Field(
        default_factory=list,
        description="Technologies used in the project.",
    )

    start_date: str | None = Field(
        default=None,
        description="Project start date.",
    )

    end_date: str | None = Field(
        default=None,
        description="Project end date.",
    )

    url: str | None = Field(
        default=None,
        description="Project URL or repository.",
    )


__all__ = ["Project"]
"""
Education Value Object.

Represents a candidate's educational qualification.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Education(BaseModel):
    """
    Immutable education value object.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    institution: str = Field(
        default="",
        description="Educational institution.",
    )

    degree: str = Field(
        default="",
        description="Degree or qualification.",
    )

    field_of_study: str | None = Field(
        default=None,
        description="Field of study.",
    )

    start_year: str | None = Field(
        default=None,
        description="Start year.",
    )

    end_year: str | None = Field(
        default=None,
        description="Completion year.",
    )

    grade: str | None = Field(
        default=None,
        description="Grade, CGPA or percentage.",
    )


__all__ = ["Education"]
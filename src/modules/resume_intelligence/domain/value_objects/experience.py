"""
Experience Value Object.

Represents a candidate's professional work experience.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Experience(BaseModel):
    """
    Immutable work experience value object.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    company: str = Field(
        default="",
        description="Company name.",
    )

    title: str = Field(
        default="",
        description="Job title.",
    )

    location: str | None = Field(
        default=None,
        description="Work location.",
    )

    start_date: str | None = Field(
        default=None,
        description="Employment start date.",
    )

    end_date: str | None = Field(
        default=None,
        description="Employment end date.",
    )

    currently_working: bool = Field(
        default=False,
        description="Whether the candidate currently works here.",
    )

    description: str | None = Field(
        default=None,
        description="Role description.",
    )


__all__ = ["Experience"]
"""
Extracted Sections Schema.

Represents the major logical sections identified within a parsed resume.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractedSections(BaseModel):
    """
    Holds the detected resume sections after section detection.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    header: str = Field(
        default="",
        description="Header section containing name and contact information.",
    )

    summary: str = Field(
        default="",
        description="Professional summary or objective.",
    )

    skills: str = Field(
        default="",
        description="Skills section.",
    )

    experience: str = Field(
        default="",
        description="Professional experience section.",
    )

    education: str = Field(
        default="",
        description="Education section.",
    )

    projects: str = Field(
        default="",
        description="Projects section.",
    )

    certifications: str = Field(
        default="",
        description="Certifications section.",
    )

    languages: str = Field(
        default="",
        description="Languages section.",
    )

    achievements: str = Field(
        default="",
        description="Achievements and awards section.",
    )

    other: str = Field(
        default="",
        description="Any remaining uncategorized content.",
    )


__all__ = ["ExtractedSections"]
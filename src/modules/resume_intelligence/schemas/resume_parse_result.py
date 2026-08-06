"""
Resume Parse Result Schema

Purpose:
    Defines the standardized output returned by every resume parser.

This model is the contract between the parser layer and the rest of the
Resume Intelligence pipeline.

Used By:
    - PDF Parser
    - DOCX Parser
    - TXT Parser
    - Candidate Builder
    - Contact Extractor
    - Section Segmenter
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeParseResult(BaseModel):
    """
    Standardized parser output.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    success: bool = Field(
        default=True,
        description="Whether parsing completed successfully.",
    )

    text: str = Field(
        default="",
        description="Extracted resume text.",
    )

    file_name: str = Field(
        default="",
        description="Original file name.",
    )

    file_size: int = Field(
        default=0,
        ge=0,
        description="File size in bytes.",
    )

    page_count: int = Field(
        default=0,
        ge=0,
        description="Number of pages.",
    )

    parser_name: str = Field(
        default="",
        description="Parser implementation.",
    )

    parser_version: str = Field(
        default="1.0.0",
        description="Parser version.",
    )

    parsed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of parsing.",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal parsing warnings.",
    )


__all__ = ["ResumeParseResult"]
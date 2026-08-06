"""
Resume Document Schema

Represents an input document before parsing.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ResumeDocument(BaseModel):
    """
    Represents a resume document before parsing.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    file_path: Path = Field(
        description="Absolute or relative path to the resume file."
    )

    file_name: str = Field(
        description="Original file name."
    )

    extension: str = Field(
        description="File extension (without leading dot)."
    )

    file_size: int = Field(
        ge=0,
        description="File size in bytes."
    )

    mime_type: str = Field(
        description="Detected MIME type."
    )

    source: str = Field(
        default="local",
        description="Source of the document."
    )

    @classmethod
    def from_file(
        cls,
        file_path: Path,
        *,
        source: str = "local",
    ) -> "ResumeDocument":
        """
        Creates a ResumeDocument from a file path.
        """

        mime_type, _ = mimetypes.guess_type(file_path)

        return cls(
            file_path=file_path,
            file_name=file_path.name,
            extension=file_path.suffix.lstrip(".").lower(),
            file_size=file_path.stat().st_size,
            mime_type=mime_type or "application/octet-stream",
            source=source,
        )


__all__ = ["ResumeDocument"]
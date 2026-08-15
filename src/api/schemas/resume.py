"""
API schemas for resume management.

Defines request and response contracts for the resume API.

This module must remain independent of FastAPI routers,
application services, repositories, and storage implementations.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.resumes.domain.entities.resume import ResumeStatus


class CreateResumeRequest(BaseModel):
    """Request body for creating a logical resume."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    name: str = Field(
        min_length=1,
        max_length=150,
    )


class ResumeResponse(BaseModel):
    """API representation of a logical resume."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    status: ResumeStatus
    created_at: datetime


class ResumeVersionResponse(BaseModel):
    """API representation of a resume version."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_id: UUID
    version_number: int
    filename: str
    file_extension: str
    storage_path: str
    file_hash: str
    file_size_bytes: int
    is_active: bool
    uploaded_at: datetime


class ResumeUploadResponse(BaseModel):
    """API response for a successfully uploaded resume."""

    model_config = ConfigDict(from_attributes=True)

    version: ResumeVersionResponse
    message: str


__all__ = [
    "CreateResumeRequest",
    "ResumeResponse",
    "ResumeVersionResponse",
    "ResumeUploadResponse",
]

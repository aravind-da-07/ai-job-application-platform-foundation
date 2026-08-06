"""
Centralized exception hierarchy.

Every custom exception in the platform inherits from `PlatformError` so
that middleware can catch, log, categorize, and translate a single base
type into a safe HTTP response without leaking internals to the client.
"""

from __future__ import annotations

from typing import Any, Optional


class PlatformError(Exception):
    """Base class for all platform-raised (as opposed to third-party/library) errors."""

    #: Machine-readable error code returned to API clients.
    code: str = "platform_error"
    #: Default HTTP status code used by the API error handler.
    http_status: int = 500

    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message, "details": self.details}


# --- Configuration -------------------------------------------------------
class ConfigurationError(PlatformError):
    code = "configuration_error"
    http_status = 500


# --- Database --------------------------------------------------------------
class DatabaseError(PlatformError):
    code = "database_error"
    http_status = 503


class RecordNotFoundError(DatabaseError):
    code = "record_not_found"
    http_status = 404


class DuplicateRecordError(DatabaseError):
    code = "duplicate_record"
    http_status = 409


# --- Validation --------------------------------------------------------------
class ValidationError(PlatformError):
    code = "validation_error"
    http_status = 422


# --- Resume / Candidate --------------------------------------------------
class ResumeParsingError(PlatformError):
    code = "resume_parsing_error"
    http_status = 422


class UnsupportedFileFormatError(ResumeParsingError):
    code = "unsupported_file_format"
    http_status = 415


# --- Job Discovery -------------------------------------------------------
class JobSourceError(PlatformError):
    code = "job_source_error"
    http_status = 502


# --- AI --------------------------------------------------------------------
class AIRequestError(PlatformError):
    code = "ai_request_error"
    http_status = 502


# --- Automation / Browser ----------------------------------------------------
class AutomationError(PlatformError):
    code = "automation_error"
    http_status = 500


class AuthenticationRequiredError(AutomationError):
    code = "authentication_required"
    http_status = 401


class CaptchaDetectedError(AutomationError):
    code = "captcha_detected"
    http_status = 423


class ManualReviewRequiredError(AutomationError):
    code = "manual_review_required"
    http_status = 409


# --- Scheduler ---------------------------------------------------------------
class SchedulerError(PlatformError):
    code = "scheduler_error"
    http_status = 500


# --- Storage --------------------------------------------------------------
class StorageError(PlatformError):
    code = "storage_error"
    http_status = 502

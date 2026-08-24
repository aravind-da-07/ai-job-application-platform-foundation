"""
Central SQLAlchemy ORM model registration.

This module imports every SQLAlchemy ORM model used by the
application so that all models are registered against the shared
Declarative Base.

Importing this module does NOT create or modify database tables.

Database schema creation and migrations remain separate concerns.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

from src.modules.users.infrastructure.models.user_model import (
    UserModel,
)


# ---------------------------------------------------------------------------
# Resumes
# ---------------------------------------------------------------------------

from src.modules.resumes.infrastructure.models.resume_model import (
    ResumeModel,
    ResumeVersionModel,
)


# ---------------------------------------------------------------------------
# Job discovery
# ---------------------------------------------------------------------------

from src.modules.job_discovery.infrastructure.models.application_model import (
    ApplicationModel,
)

from src.modules.job_discovery.infrastructure.models.job_model import (
    JobModel,
    JobMatchModel,
)


# ---------------------------------------------------------------------------
# Automation
# ---------------------------------------------------------------------------

from src.modules.automation.infrastructure.models.automation_model import (
    AutomationRunModel,
    AutomationLogModel,
)


__all__ = [
    "UserModel",
    "ResumeModel",
    "ResumeVersionModel",
    "JobModel",
    "JobMatchModel",
    "AutomationRunModel",
    "AutomationLogModel",
]
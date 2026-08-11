"""
Application domain models.

Contains portal-independent application eligibility data.
"""

from src.modules.job_discovery.domain.application.eligibility import (
    ApplicationEligibility,
    ApplicationEligibilityDecision,
)

__all__ = [
    "ApplicationEligibility",
    "ApplicationEligibilityDecision",
]
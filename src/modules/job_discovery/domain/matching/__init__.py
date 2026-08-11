"""
Job matching domain package.
"""

from src.modules.job_discovery.domain.matching.job_matching import (
    CandidateJobProfile,
    JobMatchBreakdown,
    JobMatchResult,
)

__all__ = [
    "CandidateJobProfile",
    "JobMatchBreakdown",
    "JobMatchResult",
]
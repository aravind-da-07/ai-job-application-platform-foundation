"""
Job discovery domain repository contracts.
"""

from src.modules.job_discovery.domain.repositories.job.job_repository import (
    JobRepository,
)

from src.modules.job_discovery.domain.repositories.job.job_match_repository import (
    JobMatchRepository,
)

__all__ = [
    "JobRepository",
    "JobMatchRepository",
]
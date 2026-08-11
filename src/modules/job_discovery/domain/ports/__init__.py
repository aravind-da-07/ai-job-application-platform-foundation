"""
Job discovery domain ports.
"""

from src.modules.job_discovery.domain.ports.job_portal import (
    JobPortal,
    PortalSession,
)

__all__ = [
    "JobPortal",
    "PortalSession",
]
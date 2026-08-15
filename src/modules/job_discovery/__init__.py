"""
Job discovery module.

Provides portal-independent job discovery domain entities,
portal contracts, and registry services.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    JobPortal,
    PortalSession,
)
from src.modules.job_discovery.services.portal_registry import (
    JobPortalRegistry,
)

__all__ = [
    "DiscoveredJob",
    "DiscoveryResult",
    "JobSearchCriteria",
    "JobPortal",
    "PortalSession",
    "JobPortalRegistry",
]

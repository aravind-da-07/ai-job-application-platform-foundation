"""
Job portal infrastructure adapters.

This package exposes the supported portal adapters and their
portal-specific discovery utilities.
"""

from src.modules.job_discovery.infrastructure.portals.base_portal_adapter import (
    BaseJobPortalAdapter,
)

from src.modules.job_discovery.infrastructure.portals.linkedin import (
    LinkedInJobCardExtractor,
    LinkedInPortalAdapter,
    LinkedInSearchBuilder,
)

__all__ = [
    "BaseJobPortalAdapter",
    "LinkedInJobCardExtractor",
    "LinkedInPortalAdapter",
    "LinkedInSearchBuilder",
]
"""
Job discovery infrastructure.
"""

from src.modules.job_discovery.infrastructure.browser.playwright_portal_session import (
    PlaywrightPortalSession,
)
from src.modules.job_discovery.infrastructure.portals.base_portal_adapter import (
    BaseJobPortalAdapter,
)

__all__ = [
    "BaseJobPortalAdapter",
    "PlaywrightPortalSession",
]
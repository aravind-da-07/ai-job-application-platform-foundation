"""
Job discovery orchestration service.

Coordinates:

    JobSearchCriteria
        ↓
    JobPortalRegistry
        ↓
    JobPortal
        ↓
    PortalSession
        ↓
    DiscoveryResult
        ↓
    JobDiscoveryService
        ↓
    JobRepository

This service is responsible for connecting browser-based portal
discovery with persistence.

It does not contain portal-specific selectors and does not contain
SQLAlchemy-specific persistence logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveryResult,
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    JobPortal,
)
from src.modules.job_discovery.services.discovery.job_discovery_service import (
    JobDiscoveryProcessResult,
    JobDiscoveryService,
)
from src.modules.job_discovery.services.portal_registry import (
    JobPortalRegistry,
)
from src.modules.job_discovery.infrastructure.browser.playwright_portal_session import (
    PlaywrightPortalSession,
)
from src.shared.browser.browser_engine import BrowserEngine
from src.shared.core.exceptions import (
    AuthenticationRequiredError,
)
from src.shared.logging.logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class JobDiscoveryOrchestrationResult:
    """
    Complete result of one job discovery execution.
    """

    discovery: DiscoveryResult
    processing: JobDiscoveryProcessResult
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class JobDiscoveryOrchestrator:
    """
    Coordinates browser discovery and database persistence.
    """

    def __init__(
        self,
        *,
        portal_registry: JobPortalRegistry,
        discovery_service: JobDiscoveryService,
        browser_engine: BrowserEngine | None = None,
    ) -> None:
        if portal_registry is None:
            raise ValueError(
                "portal_registry cannot be None."
            )

        if discovery_service is None:
            raise ValueError(
                "discovery_service cannot be None."
            )

        self._portal_registry = portal_registry
        self._discovery_service = discovery_service
        self._browser_engine = browser_engine

    def discover(
        self,
        *,
        source,
        criteria: JobSearchCriteria,
        storage_state: str | Path | None = None,
    ) -> JobDiscoveryOrchestrationResult:
        """
        Execute discovery for one registered portal.

        Args:
            source:
                JobSourceType identifying the portal.

            criteria:
                Portal-independent job search criteria.

            storage_state:
                Optional Playwright storage-state JSON file used for
                an existing authenticated browser session.

        Returns:
            JobDiscoveryOrchestrationResult containing the raw
            DiscoveryResult and persistence result.

        Raises:
            KeyError:
                If the requested portal is not registered.

            AuthenticationRequiredError:
                If portal authentication is required.
        """

        if criteria is None:
            raise ValueError(
                "criteria cannot be None."
            )

        portal = self._portal_registry.get(
            source
        )

        engine = (
            self._browser_engine
            if self._browser_engine is not None
            else BrowserEngine()
        )

        owns_engine = (
            self._browser_engine is None
        )

        try:
            engine.start()

            with PlaywrightPortalSession(
                engine,
                storage_state=storage_state,
            ) as session:

                logger.info(
                    "Starting job discovery: source={}",
                    source.value,
                )

                portal.authenticate(
                    session
                )

                discovery_result = self._discover_with_portal(
                    portal=portal,
                    session=session,
                    criteria=criteria,
                )

                processing_result = (
                    self._discovery_service.process(
                        discovery_result
                    )
                )

                logger.info(
                    (
                        "Job discovery completed: source={}, "
                        "found={}, persisted={}, created={}, "
                        "updated={}, failed={}"
                    ),
                    source.value,
                    discovery_result.total_found,
                    processing_result.persisted_count,
                    processing_result.created_count,
                    processing_result.updated_count,
                    processing_result.failed_count,
                )

                return JobDiscoveryOrchestrationResult(
                    discovery=discovery_result,
                    processing=processing_result,
                    metadata={
                        "source": source.value,
                        "portal": portal.name,
                        "authenticated": True,
                    },
                )

        finally:
            if owns_engine:
                engine.shutdown()

    @staticmethod
    def _discover_with_portal(
        *,
        portal: JobPortal,
        session: PlaywrightPortalSession,
        criteria: JobSearchCriteria,
    ) -> DiscoveryResult:
        """
        Execute portal-specific discovery.

        LinkedIn exposes discover_from_search_url(), while the
        generic JobPortal contract exposes discover_jobs().

        When the portal supports search URL navigation, use it.
        Otherwise fall back to discover_jobs().
        """

        discover_from_search_url = getattr(
            portal,
            "discover_from_search_url",
            None,
        )

        if callable(
            discover_from_search_url
        ):
            return discover_from_search_url(
                session,
                criteria,
            )

        return portal.discover_jobs(
            session,
            criteria,
        )


__all__ = [
    "JobDiscoveryOrchestrationResult",
    "JobDiscoveryOrchestrator",
]
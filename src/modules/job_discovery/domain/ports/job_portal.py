"""
Portal abstraction for job discovery.

The domain layer intentionally does not depend on Playwright.

Portal implementations receive a generic PortalSession contract.
The infrastructure layer is responsible for connecting that session
to BrowserEngine/Playwright.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveryResult,
    JobSearchCriteria,
)
from src.shared.config.constants import JobSourceType


@runtime_checkable
class PortalSession(Protocol):
    """
    Generic browser/session contract required by a job portal.

    The domain layer does not know whether the implementation uses
    Playwright, Selenium, an HTTP client, or another mechanism.

    The contract supports both page-level operations and scoped
    element extraction.
    """

    def navigate(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> None:
        """Navigate the active portal session."""
        ...

    def current_url(self) -> str:
        """Return the current session URL."""
        ...

    def get_text(
        self,
        selector: str,
    ) -> str:
        """Return text from the first matching page element."""
        ...

    def get_texts(
        self,
        selector: str,
    ) -> list[str]:
        """Return visible text from all matching page elements."""
        ...

    def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> str | None:
        """Return an attribute from the first matching element."""
        ...

    def get_attributes(
        self,
        selector: str,
        attribute: str,
    ) -> list[str | None]:
        """Return an attribute from all matching elements."""
        ...

    def get_scoped_text(
        self,
        parent_selector: str,
        child_selector: str,
        index: int,
    ) -> str:
        """
        Return text from a child element inside one specific parent.

        This is critical for job-card extraction because selectors
        must be scoped to the individual card.
        """
        ...

    def get_scoped_attribute(
        self,
        parent_selector: str,
        child_selector: str,
        attribute: str,
        index: int,
    ) -> str | None:
        """
        Return an attribute from a child element inside one specific
        parent element.
        """
        ...

    def get_element_count(
        self,
        selector: str,
    ) -> int:
        """Return the number of elements matching a selector."""
        ...

    def click(
        self,
        selector: str,
    ) -> None:
        """Click a page element."""
        ...


class JobPortal(ABC):
    """
    Abstract interface for a supported job portal.

    Portal adapters implement this interface.

    They must not expose Playwright-specific types to the rest
    of the application.
    """

    @property
    @abstractmethod
    def source(self) -> JobSourceType:
        """
        Return the supported job source.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return a human-readable portal name.
        """
        raise NotImplementedError

    @abstractmethod
    def is_authenticated(
        self,
        session: PortalSession,
    ) -> bool:
        """
        Determine whether the portal session is authenticated.
        """
        raise NotImplementedError

    @abstractmethod
    def authenticate(
        self,
        session: PortalSession,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Authenticate the portal session.

        CAPTCHA and MFA must never be silently bypassed.
        """
        raise NotImplementedError

    @abstractmethod
    def discover_jobs(
        self,
        session: PortalSession,
        criteria: JobSearchCriteria,
    ) -> DiscoveryResult:
        """
        Discover and normalize jobs from the portal.
        """
        raise NotImplementedError
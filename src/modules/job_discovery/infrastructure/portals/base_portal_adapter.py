"""
Base infrastructure adapter for supported job portals.

This module contains reusable portal behavior while keeping
portal-specific scraping and authentication logic inside concrete
portal adapters.

Architecture:

    JobPortal
        |
        v
    BaseJobPortalAdapter
        |
        +---- LinkedIn adapter
        +---- Indeed adapter
        +---- Naukri adapter
        |
        v
    PortalSession
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any
from urllib.parse import urlparse

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveryResult,
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    JobPortal,
    PortalSession,
)
from src.shared.config.constants import JobSourceType
from src.shared.core.exceptions import (
    AuthenticationRequiredError,
    ValidationError,
)


class BaseJobPortalAdapter(JobPortal):
    """
    Reusable base class for concrete job portal adapters.

    Responsibilities:

        - Validate portal configuration.
        - Validate search criteria.
        - Validate portal sessions.
        - Provide common navigation helpers.
        - Provide common portal metadata handling.
        - Keep concrete portal implementations focused on
          authentication and job extraction.

    Concrete adapters must implement:

        - source
        - name
        - authenticate
        - is_authenticated
        - discover_jobs
    """

    def __init__(
        self,
        *,
        base_url: str,
    ) -> None:
        normalized_url = base_url.strip()

        if not normalized_url:
            raise ValueError(
                "base_url cannot be empty."
            )

        parsed = urlparse(
            normalized_url
        )

        if parsed.scheme not in {
            "http",
            "https",
        }:
            raise ValueError(
                "base_url must use http or https."
            )

        if not parsed.netloc:
            raise ValueError(
                "base_url must contain a valid host."
            )

        self._base_url = normalized_url.rstrip("/")

    # ------------------------------------------------------------------
    # Common portal metadata
    # ------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        """
        Return the configured portal base URL.
        """

        return self._base_url

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

    # ------------------------------------------------------------------
    # Session validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_session(
        session: PortalSession,
    ) -> None:
        """
        Validate that a portal session exposes the required contract.
        """

        if session is None:
            raise ValidationError(
                "A portal session is required."
            )

        required_methods = (
            "navigate",
            "current_url",
            "get_text",
            "get_texts",
            "get_attribute",
            "get_attributes",
            "click",
        )

        missing_methods = [
            method
            for method in required_methods
            if not callable(
                getattr(
                    session,
                    method,
                    None,
                )
            )
        ]

        if missing_methods:
            raise ValidationError(
                "Portal session is missing required methods.",
                details={
                    "missing_methods": missing_methods,
                },
            )

    # ------------------------------------------------------------------
    # Search criteria validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_criteria(
        criteria: JobSearchCriteria,
    ) -> None:
        """
        Validate job-search criteria before discovery begins.
        """

        if criteria is None:
            raise ValidationError(
                "Job search criteria are required."
            )

        if not criteria.keywords:
            raise ValidationError(
                "At least one search keyword is required."
            )

        if not criteria.locations:
            raise ValidationError(
                "At least one search location is required."
            )

        if criteria.maximum_results < 1:
            raise ValidationError(
                "maximum_results must be greater than zero."
            )

    # ------------------------------------------------------------------
    # Common navigation
    # ------------------------------------------------------------------

    def open_home(
        self,
        session: PortalSession,
    ) -> None:
        """
        Navigate to the portal home page.
        """

        self._validate_session(
            session
        )

        session.navigate(
            self.base_url,
            wait_until="domcontentloaded",
        )

    def open_url(
        self,
        session: PortalSession,
        url: str,
    ) -> None:
        """
        Navigate to a validated absolute HTTP(S) URL.
        """

        self._validate_session(
            session
        )

        normalized_url = url.strip()

        if not normalized_url:
            raise ValidationError(
                "URL cannot be empty."
            )

        parsed = urlparse(
            normalized_url
        )

        if parsed.scheme not in {
            "http",
            "https",
        }:
            raise ValidationError(
                "Portal URL must use http or https."
            )

        if not parsed.netloc:
            raise ValidationError(
                "Portal URL must contain a valid host."
            )

        session.navigate(
            normalized_url,
            wait_until="domcontentloaded",
        )

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------

    def require_authentication(
        self,
        session: PortalSession,
    ) -> None:
        """
        Raise a platform-level authentication error when the
        concrete adapter determines authentication is required.

        CAPTCHA and MFA are never bypassed here.
        """

        self._validate_session(
            session
        )

        if not self.is_authenticated(
            session
        ):
            raise AuthenticationRequiredError(
                f"Authentication is required for {self.name}."
            )

    # ------------------------------------------------------------------
    # Portal state helpers
    # ------------------------------------------------------------------

    def is_on_portal(
        self,
        session: PortalSession,
    ) -> bool:
        """
        Return True when the current URL belongs to this portal.

        This performs hostname comparison only. It does not attempt
        to determine authentication state.
        """

        self._validate_session(
            session
        )

        current_url = (
            session.current_url()
            .strip()
        )

        if not current_url:
            return False

        current_host = (
            urlparse(
                current_url
            ).hostname
            or ""
        ).lower()

        portal_host = (
            urlparse(
                self.base_url
            ).hostname
            or ""
        ).lower()

        if not current_host or not portal_host:
            return False

        return (
            current_host == portal_host
            or current_host.endswith(
                f".{portal_host}"
            )
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @staticmethod
    def merge_metadata(
        base: dict[str, Any] | None,
        additional: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Return a new metadata dictionary.

        Neither input dictionary is modified.

        Values from additional take precedence.
        """

        result = dict(
            base or {}
        )

        result.update(
            additional or {}
        )

        return result

    # ------------------------------------------------------------------
    # Required JobPortal operations
    # ------------------------------------------------------------------

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
        Authenticate against the concrete portal.

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
        Discover and normalize jobs from the concrete portal.
        """

        raise NotImplementedError
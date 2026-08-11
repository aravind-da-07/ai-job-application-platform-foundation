"""
Registry for supported job portals.

The registry maps JobSourceType values to portal implementations.
"""

from __future__ import annotations

from src.modules.job_discovery.domain.ports.job_portal import JobPortal
from src.shared.config.constants import JobSourceType


class JobPortalRegistry:
    """
    Stores and resolves registered job portal adapters.
    """

    def __init__(self) -> None:
        self._portals: dict[
            JobSourceType,
            JobPortal,
        ] = {}

    def register(
        self,
        portal: JobPortal,
    ) -> None:
        """
        Register a portal implementation.

        Existing implementations for the same source are replaced.
        """

        if not isinstance(portal, JobPortal):
            raise TypeError(
                "portal must implement JobPortal."
            )

        self._portals[portal.source] = portal

    def unregister(
        self,
        source: JobSourceType,
    ) -> None:
        """
        Remove a portal implementation.
        """

        if source not in self._portals:
            raise KeyError(
                f"Portal '{source.value}' is not registered."
            )

        del self._portals[source]

    def get(
        self,
        source: JobSourceType,
    ) -> JobPortal:
        """
        Return the registered portal for a source.
        """

        portal = self._portals.get(source)

        if portal is None:
            raise KeyError(
                f"Portal '{source.value}' is not registered."
            )

        return portal

    def has(
        self,
        source: JobSourceType,
    ) -> bool:
        """
        Return True if a portal is registered.
        """

        return source in self._portals

    def list_sources(self) -> list[JobSourceType]:
        """
        Return registered source types.
        """

        return sorted(
            self._portals.keys(),
            key=lambda source: source.value,
        )

    def list_portals(self) -> list[JobPortal]:
        """
        Return registered portal implementations.
        """

        return list(self._portals.values())
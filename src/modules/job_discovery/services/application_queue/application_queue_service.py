"""
Application queue service.

Responsible for converting eligible jobs into application queue items.

This service is intentionally independent of:
    - Playwright
    - Selenium
    - databases
    - HTTP clients
    - individual job portals

The application runner will consume the queue later.
"""

from __future__ import annotations

from uuid import uuid4

from src.modules.job_discovery.domain.application_queue import (
    ApplicationQueueDecision,
    ApplicationQueueItem,
)
from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.shared.config.constants import (
    ApplicationStatus,
)


class ApplicationQueueService:
    """
    In-memory application queue service.

    This is the application-layer queue abstraction.

    A persistent repository can be connected later without changing
    the domain model or the application runner contract.
    """

    def __init__(
        self,
        *,
        maximum_queue_size: int = 1000,
        default_max_attempts: int = 3,
    ) -> None:
        if maximum_queue_size < 1:
            raise ValueError(
                "maximum_queue_size must be greater than zero."
            )

        if default_max_attempts < 1:
            raise ValueError(
                "default_max_attempts must be greater than zero."
            )

        self._maximum_queue_size = maximum_queue_size
        self._default_max_attempts = default_max_attempts

        self._items: dict[
            str,
            ApplicationQueueItem,
        ] = {}

        self._job_index: dict[
            str,
            str,
        ] = {}

    # ------------------------------------------------------------------
    # Queue properties
    # ------------------------------------------------------------------

    @property
    def maximum_queue_size(self) -> int:
        """Return the maximum number of queued items."""
        return self._maximum_queue_size

    @property
    def size(self) -> int:
        """Return the current number of queue items."""
        return len(self._items)

    # ------------------------------------------------------------------
    # Queue insertion
    # ------------------------------------------------------------------

    def enqueue(
        self,
        job: DiscoveredJob,
        *,
        match_score: float,
        priority: int = 0,
        metadata: dict | None = None,
    ) -> ApplicationQueueDecision:
        """
        Add an eligible job to the application queue.

        Duplicate external job IDs are rejected.

        Only jobs with a valid normalized representation are accepted.
        """

        if job is None:
            raise ValueError(
                "job is required."
            )

        if not 0.0 <= match_score <= 1.0:
            raise ValueError(
                "match_score must be between 0 and 1."
            )

        if priority < 0:
            raise ValueError(
                "priority cannot be negative."
            )

        external_job_id = job.external_id.strip()

        if not external_job_id:
            raise ValueError(
                "job.external_id cannot be empty."
            )

        # --------------------------------------------------------------
        # Duplicate protection
        # --------------------------------------------------------------

        if external_job_id in self._job_index:
            return ApplicationQueueDecision(
                accepted=False,
                reason=(
                    "Application already exists in the queue "
                    "for this job."
                ),
                duplicate=True,
                metadata={
                    "external_job_id": external_job_id,
                },
            )

        # --------------------------------------------------------------
        # Queue capacity
        # --------------------------------------------------------------

        if self.size >= self.maximum_queue_size:
            return ApplicationQueueDecision(
                accepted=False,
                reason=(
                    "Application queue has reached its "
                    "maximum capacity."
                ),
                queue_full=True,
                metadata={
                    "queue_size": self.size,
                    "maximum_queue_size": (
                        self.maximum_queue_size
                    ),
                },
            )

        # --------------------------------------------------------------
        # Create queue item
        # --------------------------------------------------------------

        application_id = (
            f"app-{uuid4().hex}"
        )

        item = ApplicationQueueItem(
            application_id=application_id,
            external_job_id=external_job_id,
            job_title=job.title,
            company_name=job.company_name,
            job_url=job.url,
            source=job.source,
            match_score=match_score,
            priority=priority,
            status=ApplicationStatus.QUEUED,
            attempt_count=0,
            max_attempts=self._default_max_attempts,
            metadata=dict(metadata or {}),
        )

        self._items[application_id] = item
        self._job_index[external_job_id] = application_id

        return ApplicationQueueDecision(
            accepted=True,
            reason=(
                "Job successfully added to the "
                "application queue."
            ),
            item=item,
            metadata={
                "application_id": application_id,
                "external_job_id": external_job_id,
            },
        )

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(
        self,
        application_id: str,
    ) -> ApplicationQueueItem | None:
        """
        Return a queue item by application ID.
        """

        return self._items.get(
            application_id
        )

    def get_by_job(
        self,
        external_job_id: str,
    ) -> ApplicationQueueItem | None:
        """
        Return the queue item associated with an external job ID.
        """

        application_id = self._job_index.get(
            external_job_id
        )

        if application_id is None:
            return None

        return self._items.get(
            application_id
        )

    # ------------------------------------------------------------------
    # Queue inspection
    # ------------------------------------------------------------------

    def list_items(
        self,
    ) -> list[ApplicationQueueItem]:
        """
        Return all queue items.

        Higher priority items are returned first.
        """

        return sorted(
            self._items.values(),
            key=lambda item: (
                -item.priority,
                -item.match_score,
                item.created_at,
            ),
        )

    def queued_items(
        self,
    ) -> list[ApplicationQueueItem]:
        """
        Return only items currently waiting for execution.
        """

        return [
            item
            for item in self.list_items()
            if item.status
            == ApplicationStatus.QUEUED
        ]

    # ------------------------------------------------------------------
    # Queue state
    # ------------------------------------------------------------------

    def contains_job(
        self,
        external_job_id: str,
    ) -> bool:
        """
        Return True when the job already exists in the queue.
        """

        return external_job_id in self._job_index

    def remove(
        self,
        application_id: str,
    ) -> ApplicationQueueItem | None:
        """
        Remove an application from the in-memory queue.
        """

        item = self._items.pop(
            application_id,
            None,
        )

        if item is None:
            return None

        self._job_index.pop(
            item.external_job_id,
            None,
        )

        return item

    def clear(self) -> None:
        """
        Clear the entire in-memory queue.
        """

        self._items.clear()
        self._job_index.clear()
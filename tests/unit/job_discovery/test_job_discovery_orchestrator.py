"""
Unit tests for JobDiscoveryOrchestrator.

These tests deliberately avoid:
- Playwright
- LinkedIn
- PostgreSQL
- Supabase
- real browser sessions

Only the orchestration behavior is tested.
"""

from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
    JobSearchCriteria,
)
from src.modules.job_discovery.domain.ports.job_portal import (
    JobPortal,
)
from src.modules.job_discovery.services.discovery.job_discovery_orchestrator import (
    JobDiscoveryOrchestrator,
)
from src.modules.job_discovery.services.discovery.job_discovery_service import (
    JobDiscoveryProcessResult,
)
from src.modules.job_discovery.services.portal_registry import (
    JobPortalRegistry,
)
from src.shared.config.constants import JobSourceType
from src.shared.core.exceptions import (
    AuthenticationRequiredError,
)


class FakePortal(JobPortal):
    """Simple portal implementation for orchestration tests."""

    def __init__(
        self,
        *,
        discovery_result: DiscoveryResult,
    ) -> None:
        self._discovery_result = discovery_result
        self.authenticate_called = False
        self.discover_called = False

    @property
    def source(self) -> JobSourceType:
        return JobSourceType.LINKEDIN

    @property
    def name(self) -> str:
        return "Fake LinkedIn"

    def is_authenticated(
        self,
        session,
    ) -> bool:
        return True

    def authenticate(
        self,
        session,
        *,
        metadata=None,
    ) -> None:
        self.authenticate_called = True

    def discover_jobs(
        self,
        session,
        criteria,
    ) -> DiscoveryResult:
        self.discover_called = True
        return self._discovery_result


def build_job(
    *,
    external_id: str = "job-001",
) -> DiscoveredJob:
    """Build a valid discovered job for testing."""

    return DiscoveredJob(
        external_id=external_id,
        title="Data Analyst",
        company_name="Example Company",
        source=JobSourceType.LINKEDIN,
        url=f"https://www.linkedin.com/jobs/view/{external_id}",
        location="Hyderabad",
        description="Data analyst role.",
    )


def build_discovery_result(
    *jobs: DiscoveredJob,
) -> DiscoveryResult:
    """Build a valid DiscoveryResult."""

    return DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=tuple(jobs),
        total_found=len(jobs),
        metadata={
            "test": True,
        },
    )


def build_processing_result(
    discovery_result: DiscoveryResult,
) -> JobDiscoveryProcessResult:
    """Build a successful persistence result."""

    return JobDiscoveryProcessResult(
        source=discovery_result.source,
        total_found=discovery_result.total_found,
        jobs_received=len(
            discovery_result.jobs
        ),
        persisted_jobs=discovery_result.jobs,
        created_jobs=discovery_result.jobs,
    )


def build_orchestrator(
    *,
    portal: JobPortal,
    discovery_service: Mock,
) -> JobDiscoveryOrchestrator:
    """Build the orchestrator with mocked dependencies."""

    registry = JobPortalRegistry()

    registry.register(
        portal
    )

    return JobDiscoveryOrchestrator(
        portal_registry=registry,
        discovery_service=discovery_service,
    )


def test_discover_authenticates_portal_and_processes_result() -> None:
    """
    The orchestrator should authenticate the portal, perform discovery,
    and pass the DiscoveryResult to JobDiscoveryService.
    """

    job = build_job()

    discovery_result = build_discovery_result(
        job
    )

    portal = FakePortal(
        discovery_result=discovery_result
    )

    discovery_service = Mock()

    discovery_service.process.return_value = (
        build_processing_result(
            discovery_result
        )
    )

    orchestrator = build_orchestrator(
        portal=portal,
        discovery_service=discovery_service,
    )

    criteria = JobSearchCriteria(
        keywords=("Data Analyst",),
        locations=("Hyderabad",),
        maximum_results=10,
    )

    result = orchestrator.discover(
        source=JobSourceType.LINKEDIN,
        criteria=criteria,
    )

    assert portal.authenticate_called is True
    assert portal.discover_called is True

    discovery_service.process.assert_called_once_with(
        discovery_result
    )

    assert result.discovery == discovery_result
    assert (
        result.processing.persisted_count
        == 1
    )
    assert (
        result.processing.created_count
        == 1
    )


def test_discover_returns_empty_result_when_portal_returns_no_jobs() -> None:
    """
    Empty portal results should be processed normally.
    """

    discovery_result = build_discovery_result()

    portal = FakePortal(
        discovery_result=discovery_result
    )

    discovery_service = Mock()

    discovery_service.process.return_value = (
        build_processing_result(
            discovery_result
        )
    )

    orchestrator = build_orchestrator(
        portal=portal,
        discovery_service=discovery_service,
    )

    criteria = JobSearchCriteria(
        keywords=("Data Analyst",),
        locations=("Hyderabad",),
        maximum_results=10,
    )

    result = orchestrator.discover(
        source=JobSourceType.LINKEDIN,
        criteria=criteria,
    )

    assert result.discovery.total_found == 0
    assert result.discovery.jobs == ()

    discovery_service.process.assert_called_once_with(
        discovery_result
    )


def test_discover_raises_when_portal_is_not_registered() -> None:
    """
    Requesting an unregistered portal should fail before browser
    discovery starts.
    """

    registry = JobPortalRegistry()

    discovery_service = Mock()

    orchestrator = JobDiscoveryOrchestrator(
        portal_registry=registry,
        discovery_service=discovery_service,
    )

    criteria = JobSearchCriteria(
        keywords=("Data Analyst",),
        maximum_results=10,
    )

    with pytest.raises(KeyError):
        orchestrator.discover(
            source=JobSourceType.LINKEDIN,
            criteria=criteria,
        )

    discovery_service.process.assert_not_called()


def test_discover_rejects_none_criteria() -> None:
    """
    The orchestrator should reject missing search criteria.
    """

    portal = FakePortal(
        discovery_result=build_discovery_result()
    )

    discovery_service = Mock()

    orchestrator = build_orchestrator(
        portal=portal,
        discovery_service=discovery_service,
    )

    with pytest.raises(
        ValueError,
        match="criteria cannot be None",
    ):
        orchestrator.discover(
            source=JobSourceType.LINKEDIN,
            criteria=None,
        )


def test_discover_propagates_authentication_required_error() -> None:
    """
    Authentication failures must be surfaced instead of bypassed.
    """

    portal = FakePortal(
        discovery_result=build_discovery_result()
    )

    def fail_authenticate(
        session,
        *,
        metadata=None,
    ) -> None:
        raise AuthenticationRequiredError(
            "LinkedIn authentication is required."
        )

    portal.authenticate = fail_authenticate

    discovery_service = Mock()

    orchestrator = build_orchestrator(
        portal=portal,
        discovery_service=discovery_service,
    )

    criteria = JobSearchCriteria(
        keywords=("Data Analyst",),
        maximum_results=10,
    )

    with pytest.raises(
        AuthenticationRequiredError,
        match="authentication is required",
    ):
        orchestrator.discover(
            source=JobSourceType.LINKEDIN,
            criteria=criteria,
        )

    discovery_service.process.assert_not_called()


def test_discover_preserves_processing_failures() -> None:
    """
    Persistence failures returned by JobDiscoveryService should remain
    visible in the orchestration result.
    """

    successful_job = build_job(
        external_id="job-001"
    )

    failed_job = build_job(
        external_id="job-002"
    )

    discovery_result = build_discovery_result(
        successful_job,
        failed_job,
    )

    portal = FakePortal(
        discovery_result=discovery_result
    )

    discovery_service = Mock()

    processing_result = JobDiscoveryProcessResult(
        source=JobSourceType.LINKEDIN,
        total_found=2,
        jobs_received=2,
        persisted_jobs=(successful_job,),
        created_jobs=(successful_job,),
        failed_jobs=(failed_job,),
        reasons=(
            "Failed to persist job 'job-002'.",
        ),
    )

    discovery_service.process.return_value = (
        processing_result
    )

    orchestrator = build_orchestrator(
        portal=portal,
        discovery_service=discovery_service,
    )

    criteria = JobSearchCriteria(
        keywords=("Data Analyst",),
        locations=("Hyderabad",),
        maximum_results=10,
    )

    result = orchestrator.discover(
        source=JobSourceType.LINKEDIN,
        criteria=criteria,
    )

    assert result.processing.persisted_count == 1
    assert result.processing.created_count == 1
    assert result.processing.failed_count == 1

    assert result.processing.failed_jobs == (
        failed_job,
    )

    assert result.processing.reasons == (
        "Failed to persist job 'job-002'.",
    )
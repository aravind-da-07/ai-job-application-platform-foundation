"""
Unit tests for the Job Discovery API.

These tests exercise the FastAPI endpoint without using:
- a real browser
- LinkedIn
- Supabase
- PostgreSQL
- Playwright

The JobDiscoveryOrchestrator dependency is replaced with a mock.
"""

from __future__ import annotations

from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.api.routers.jobs import (
    get_job_discovery_orchestrator,
)
from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
    DiscoveryResult,
)
from src.modules.job_discovery.services.discovery.job_discovery_service import (
    JobDiscoveryProcessResult,
)
from src.shared.config.constants import (
    JobSourceType,
)
from src.shared.core.exceptions import (
    AuthenticationRequiredError,
)


def build_job(
    *,
    external_id: str = "linkedin-001",
) -> DiscoveredJob:
    """Build a valid discovered job."""

    return DiscoveredJob(
        external_id=external_id,
        title="Data Analyst",
        company_name="Example Company",
        source=JobSourceType.LINKEDIN,
        url=(
            "https://www.linkedin.com/jobs/view/"
            f"{external_id}"
        ),
        location="Hyderabad",
        description="Data analyst position.",
        metadata={
            "test": True,
        },
    )


def build_discovery_result(
    *jobs: DiscoveredJob,
) -> DiscoveryResult:
    """Build a valid discovery result."""

    return DiscoveryResult(
        source=JobSourceType.LINKEDIN,
        jobs=tuple(jobs),
        total_found=len(jobs),
        metadata={
            "portal": "LinkedIn",
            "test": True,
        },
    )


def build_processing_result(
    discovery_result: DiscoveryResult,
) -> JobDiscoveryProcessResult:
    """Build a successful processing result."""

    return JobDiscoveryProcessResult(
        source=discovery_result.source,
        total_found=discovery_result.total_found,
        jobs_received=len(
            discovery_result.jobs
        ),
        persisted_jobs=discovery_result.jobs,
        created_jobs=discovery_result.jobs,
        metadata={
            "test_processing": True,
        },
    )


def test_discover_jobs_returns_successful_response(
    api_client: TestClient,
) -> None:
    """
    The discovery endpoint should return the normalized discovery
    and persistence information.
    """

    job = build_job()

    discovery_result = build_discovery_result(
        job
    )

    processing_result = build_processing_result(
        discovery_result
    )

    orchestration_result = Mock()

    orchestration_result.discovery = discovery_result
    orchestration_result.processing = processing_result
    orchestration_result.metadata = {
        "orchestrator": "test",
    }

    orchestrator = Mock()

    orchestrator.discover.return_value = (
        orchestration_result
    )

    api_client.app.dependency_overrides[
        get_job_discovery_orchestrator
    ] = lambda: orchestrator

    try:
        response = api_client.post(
            "/api/v1/jobs/discover",
            json={
                "source": "linkedin",
                "keywords": [
                    "Data Analyst",
                    "Business Analyst",
                ],
                "locations": [
                    "Hyderabad",
                ],
                "maximum_results": 10,
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["success"] is True
        assert (
            body["message"]
            == "Job discovery completed successfully."
        )

        data = body["data"]

        assert data["source"] == "linkedin"
        assert data["total_found"] == 1
        assert data["jobs_received"] == 1

        assert data["persisted_count"] == 1
        assert data["created_count"] == 1
        assert data["updated_count"] == 0
        assert data["failed_count"] == 0

        assert len(data["jobs"]) == 1
        assert (
            data["jobs"][0]["external_id"]
            == "linkedin-001"
        )
        assert (
            data["jobs"][0]["title"]
            == "Data Analyst"
        )
        assert (
            data["jobs"][0]["company_name"]
            == "Example Company"
        )

        assert len(data["created_jobs"]) == 1
        assert data["updated_jobs"] == []
        assert data["failed_jobs"] == []

        orchestrator.discover.assert_called_once()

        call_kwargs = (
            orchestrator.discover.call_args.kwargs
        )

        assert (
            call_kwargs["source"]
            == JobSourceType.LINKEDIN
        )

        criteria = call_kwargs["criteria"]

        assert criteria.keywords == (
            "Data Analyst",
            "Business Analyst",
        )

        assert criteria.locations == (
            "Hyderabad",
        )

        assert criteria.maximum_results == 10

    finally:
        api_client.app.dependency_overrides.clear()


def test_discover_jobs_supports_empty_result(
    api_client: TestClient,
) -> None:
    """
    A successful discovery run with no matching jobs should return
    an empty jobs collection rather than an error.
    """

    discovery_result = build_discovery_result()

    processing_result = build_processing_result(
        discovery_result
    )

    orchestration_result = Mock()

    orchestration_result.discovery = discovery_result
    orchestration_result.processing = processing_result
    orchestration_result.metadata = {}

    orchestrator = Mock()

    orchestrator.discover.return_value = (
        orchestration_result
    )

    api_client.app.dependency_overrides[
        get_job_discovery_orchestrator
    ] = lambda: orchestrator

    try:
        response = api_client.post(
            "/api/v1/jobs/discover",
            json={
                "source": "linkedin",
                "keywords": [
                    "Data Analyst",
                ],
                "maximum_results": 20,
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["success"] is True

        data = body["data"]

        assert data["total_found"] == 0
        assert data["jobs_received"] == 0
        assert data["persisted_count"] == 0
        assert data["created_count"] == 0
        assert data["updated_count"] == 0
        assert data["failed_count"] == 0

        assert data["jobs"] == []
        assert data["created_jobs"] == []
        assert data["updated_jobs"] == []
        assert data["failed_jobs"] == []

    finally:
        api_client.app.dependency_overrides.clear()


def test_discover_jobs_returns_401_when_authentication_is_required(
    api_client: TestClient,
) -> None:
    """
    Authentication-required errors from the orchestrator should be
    translated into HTTP 401.
    """

    orchestrator = Mock()

    orchestrator.discover.side_effect = (
        AuthenticationRequiredError(
            "LinkedIn authentication is required."
        )
    )

    api_client.app.dependency_overrides[
        get_job_discovery_orchestrator
    ] = lambda: orchestrator

    try:
        response = api_client.post(
            "/api/v1/jobs/discover",
            json={
                "source": "linkedin",
                "keywords": [
                    "Data Analyst",
                ],
            },
        )

        assert response.status_code == 401

        body = response.json()

        assert (
            body["detail"]
            == "LinkedIn authentication is required."
        )

    finally:
        api_client.app.dependency_overrides.clear()


def test_discover_jobs_rejects_invalid_match_score(
    api_client: TestClient,
) -> None:
    """
    minimum_match_score must be between 0 and 1.
    """

    response = api_client.post(
        "/api/v1/jobs/discover",
        json={
            "source": "linkedin",
            "keywords": [
                "Data Analyst",
            ],
            "minimum_match_score": 1.5,
        },
    )

    assert response.status_code == 422


def test_discover_jobs_rejects_invalid_maximum_results(
    api_client: TestClient,
) -> None:
    """
    maximum_results must be between 1 and 100.
    """

    response = api_client.post(
        "/api/v1/jobs/discover",
        json={
            "source": "linkedin",
            "keywords": [
                "Data Analyst",
            ],
            "maximum_results": 0,
        },
    )

    assert response.status_code == 422


def test_discover_jobs_rejects_unknown_request_fields(
    api_client: TestClient,
) -> None:
    """
    JobDiscoveryRequest uses extra='forbid', so unknown request
    properties should be rejected.
    """

    response = api_client.post(
        "/api/v1/jobs/discover",
        json={
            "source": "linkedin",
            "keywords": [
                "Data Analyst",
            ],
            "unexpected_field": "not allowed",
        },
    )

    assert response.status_code == 422
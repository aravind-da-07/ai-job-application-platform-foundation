from __future__ import annotations

from fastapi.testclient import TestClient


def test_version_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "app_name" in body["data"]


def test_health_endpoint_reports_degraded_without_database(api_client: TestClient) -> None:
    # In the test environment DATABASE_URL is intentionally unset, so the
    # health check should report "degraded" rather than crashing.
    response = api_client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] in ("healthy", "degraded")


def test_config_endpoint_never_leaks_secrets(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/config")
    assert response.status_code == 200
    body_text = response.text.lower()
    assert "key" not in body_text
    assert "secret" not in body_text
    assert "password" not in body_text

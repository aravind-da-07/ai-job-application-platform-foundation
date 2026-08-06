"""System-level endpoints: health check, version, and (non-secret) config."""

from __future__ import annotations

from fastapi import APIRouter

from src.shared.config.settings import get_settings
from src.shared.database.session import check_database_health
from src.shared.schemas.response_models import APIResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=APIResponse)
def health_check() -> APIResponse:
    """
    Liveness/readiness probe. Checks database connectivity so that
    orchestrators (Docker healthcheck, k8s probes) can detect a broken
    database connection, not just a running process.
    """
    settings = get_settings()
    db_healthy = False
    db_error: str | None = None
    if settings.database_url:
        try:
            db_healthy = check_database_health()
        except Exception as exc:  # noqa: BLE001
            db_error = str(exc)
    else:
        db_error = "DATABASE_URL not configured"

    return APIResponse(
        success=db_healthy,
        data={
            "status": "healthy" if db_healthy else "degraded",
            "database_connected": db_healthy,
            "database_error": db_error,
            "environment": settings.environment.value,
        },
    )


@router.get("/version", response_model=APIResponse)
def version() -> APIResponse:
    settings = get_settings()
    return APIResponse(data={"app_name": settings.app_name, "version": settings.app_version})


@router.get("/config", response_model=APIResponse)
def public_config() -> APIResponse:
    """Returns only non-secret configuration values — never keys or URLs with credentials."""
    settings = get_settings()
    return APIResponse(
        data={
            "environment": settings.environment.value,
            "minimum_match_score_to_apply": settings.minimum_match_score_to_apply,
            "manual_review_match_score": settings.manual_review_match_score,
            "dashboard_refresh_seconds": settings.dashboard_refresh_seconds,
        }
    )

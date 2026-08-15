"""
Job discovery API.

The router is intentionally thin.

Browser automation is handled by the discovery orchestration
service, while database persistence is handled by the repository
layer.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from src.api.schemas.job_discovery import (
    DiscoveredJobResponse,
    JobDiscoveryRequest,
    JobDiscoveryResponse,
)
from src.modules.job_discovery.domain.entities.job_discovery import (
    JobSearchCriteria,
)
from src.modules.job_discovery.infrastructure.repositories.job.job_repository_impl import (
    SQLAlchemyJobRepository,
)
from src.modules.job_discovery.infrastructure.portals.linkedin.linkedin_portal import (
    LinkedInPortalAdapter,
)
from src.modules.job_discovery.services.discovery.job_discovery_orchestrator import (
    JobDiscoveryOrchestrator,
)
from src.modules.job_discovery.services.discovery.job_discovery_service import (
    JobDiscoveryService,
)
from src.modules.job_discovery.services.portal_registry import (
    JobPortalRegistry,
)
from src.shared.config.constants import JobSourceType
from src.shared.core.exceptions import (
    AuthenticationRequiredError,
)
from src.shared.database.session import get_db_session
from src.shared.schemas.response_models import APIResponse


router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
)


def get_job_discovery_orchestrator(
    db: Session = Depends(get_db_session),
) -> JobDiscoveryOrchestrator:
    """
    Build the job discovery orchestration service.
    """

    repository = SQLAlchemyJobRepository(
        db
    )

    discovery_service = JobDiscoveryService(
        repository
    )

    registry = JobPortalRegistry()

    registry.register(
        LinkedInPortalAdapter()
    )

    return JobDiscoveryOrchestrator(
        portal_registry=registry,
        discovery_service=discovery_service,
    )


@router.post(
    "/discover",
    response_model=APIResponse[JobDiscoveryResponse],
    status_code=status.HTTP_200_OK,
)
def discover_jobs(
    request: JobDiscoveryRequest,
    orchestrator: JobDiscoveryOrchestrator = Depends(
        get_job_discovery_orchestrator
    ),
) -> APIResponse[JobDiscoveryResponse]:
    """
    Discover jobs from a supported job portal.

    Currently LinkedIn is the first supported portal.
    """

    criteria = JobSearchCriteria(
        keywords=tuple(
            keyword.strip()
            for keyword in request.keywords
            if keyword.strip()
        ),
        locations=tuple(
            location.strip()
            for location in request.locations
            if location.strip()
        ),
        remote_statuses=tuple(
            request.remote_statuses
        ),
        employment_types=tuple(
            request.employment_types
        ),
        minimum_match_score=(
            request.minimum_match_score
        ),
        maximum_results=request.maximum_results,
    )

    try:
        result = orchestrator.discover(
            source=request.source,
            criteria=criteria,
            storage_state=request.storage_state,
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AuthenticationRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    response = JobDiscoveryResponse(
        source=result.discovery.source,
        total_found=result.discovery.total_found,
        jobs_received=len(
            result.discovery.jobs
        ),
        persisted_count=(
            result.processing.persisted_count
        ),
        created_count=(
            result.processing.created_count
        ),
        updated_count=(
            result.processing.updated_count
        ),
        failed_count=(
            result.processing.failed_count
        ),
        jobs=[
            DiscoveredJobResponse(
                **job.__dict__
            )
            for job in result.discovery.jobs
        ],
        created_jobs=[
            DiscoveredJobResponse(
                **job.__dict__
            )
            for job in result.processing.created_jobs
        ],
        updated_jobs=[
            DiscoveredJobResponse(
                **job.__dict__
            )
            for job in result.processing.updated_jobs
        ],
        failed_jobs=[
            DiscoveredJobResponse(
                **job.__dict__
            )
            for job in result.processing.failed_jobs
        ],
        reasons=list(
            result.processing.reasons
        ),
        metadata={
            **result.processing.metadata,
            **result.metadata,
        },
    )

    return APIResponse(
        success=True,
        data=response,
        message="Job discovery completed successfully.",
    )


__all__ = [
    "router",
]
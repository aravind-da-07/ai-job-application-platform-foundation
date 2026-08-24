"""
Application queue API.

This router exposes the application-queue boundary.

Responsibilities:
    - Validate application queue requests.
    - Load persisted jobs.
    - Build the domain candidate profile.
    - Run matching and eligibility.
    - Persist eligible applications.

This router does not:
    - open browsers,
    - authenticate against job portals,
    - fill application forms,
    - submit applications.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from src.api.schemas.application import (
    ApplicationQueueRequest,
    ApplicationQueueResponse,
    ApplicationQueueResult,
)
from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.domain.matching import (
    CandidateJobProfile,
)
from src.modules.job_discovery.infrastructure.models.job_model import (
    JobModel,
)
from src.modules.job_discovery.infrastructure.repositories.application_repository_impl import (
    SQLAlchemyApplicationRepository,
)
from src.modules.job_discovery.services.application_pipeline import (
    ApplicationPipelineService,
)
from src.shared.config.constants import (
    EmploymentType,
    JobSourceType,
    RemoteStatus,
)
from src.shared.database.session import get_db_session
from src.shared.schemas.response_models import APIResponse


router = APIRouter(
    prefix="/applications",
    tags=["applications"],
)


# ----------------------------------------------------------------------
# Domain conversion helpers
# ----------------------------------------------------------------------


def _convert_remote_status(
    remote: bool | None,
) -> RemoteStatus | None:
    """
    Convert the database boolean representation into the
    domain RemoteStatus enum.
    """

    if remote is None:
        return None

    return (
        RemoteStatus.REMOTE
        if remote
        else RemoteStatus.ON_SITE
    )


def _convert_employment_type(
    value: str | None,
) -> EmploymentType | None:
    """
    Convert the persisted employment type into the domain enum.
    """

    if value is None:
        return None

    try:
        return EmploymentType(value)
    except ValueError:
        return None


def _convert_source(
    value: JobSourceType | str,
) -> JobSourceType:
    """
    Convert the persisted source into JobSourceType.
    """

    if isinstance(value, JobSourceType):
        return value

    return JobSourceType(value)


def _job_model_to_domain(
    model: JobModel,
) -> DiscoveredJob:
    """
    Convert a persisted JobModel into the domain DiscoveredJob.
    """

    return DiscoveredJob(
        external_id=model.external_job_id,
        title=model.title,
        company_name=model.company_name,
        source=_convert_source(
            model.source
        ),
        url=model.url,
        location=model.location,
        remote_status=_convert_remote_status(
            model.remote
        ),
        employment_type=_convert_employment_type(
            model.employment_type
        ),
        description=model.description,
        posted_at=(
            model.posted_at.isoformat()
            if model.posted_at is not None
            else None
        ),
        salary_min=(
            float(model.salary_min)
            if model.salary_min is not None
            else None
        ),
        salary_max=(
            float(model.salary_max)
            if model.salary_max is not None
            else None
        ),
        salary_currency=model.salary_currency,
        metadata=dict(
            model.metadata_json or {}
        ),
    )


def _build_candidate_profile(
    request: ApplicationQueueRequest,
) -> CandidateJobProfile:
    """
    Build the domain CandidateJobProfile from the API request.
    """

    return CandidateJobProfile(
        target_roles=tuple(
            value.strip()
            for value in request.target_roles
            if value.strip()
        ),
        preferred_locations=tuple(
            value.strip()
            for value in request.preferred_locations
            if value.strip()
        ),
        preferred_remote_statuses=tuple(
            value.strip()
            for value in request.preferred_remote_statuses
            if value.strip()
        ),
        required_skills=tuple(
            value.strip()
            for value in request.required_skills
            if value.strip()
        ),
        preferred_skills=tuple(
            value.strip()
            for value in request.preferred_skills
            if value.strip()
        ),
        excluded_roles=tuple(
            value.strip()
            for value in request.excluded_roles
            if value.strip()
        ),
        excluded_companies=tuple(
            value.strip()
            for value in request.excluded_companies
            if value.strip()
        ),
        minimum_experience_years=(
            request.minimum_experience_years
        ),
        maximum_experience_years=(
            request.maximum_experience_years
        ),
        minimum_match_score=(
            request.minimum_match_score
        ),
        metadata=dict(
            request.metadata
        ),
    )


# ----------------------------------------------------------------------
# Response helper
# ----------------------------------------------------------------------


def _queue_item_to_response(
    *,
    queue_item,
    request: ApplicationQueueRequest,
) -> ApplicationQueueResponse:
    """
    Convert an ApplicationQueueItem into an API response.
    """

    return ApplicationQueueResponse(
        application_id=queue_item.application_id,
        user_id=request.user_id,
        job_id=request.job_id,
        resume_id=request.resume_id,
        resume_version_id=(
            request.resume_version_id
        ),
        external_job_id=queue_item.external_job_id,
        source=(
            queue_item.source.value
            if hasattr(
                queue_item.source,
                "value",
            )
            else str(
                queue_item.source
            )
        ),
        job_url=queue_item.job_url,
        job_title=queue_item.job_title,
        company_name=queue_item.company_name,
        match_score=queue_item.match_score,
        status=queue_item.status,
        priority=queue_item.priority,
        attempt_count=queue_item.attempt_count,
        max_attempts=queue_item.max_attempts,
        queued_at=queue_item.created_at,
        metadata=dict(
            queue_item.metadata
        ),
    )


# ----------------------------------------------------------------------
# Queue endpoint
# ----------------------------------------------------------------------


@router.post(
    "/queue",
    response_model=APIResponse[ApplicationQueueResult],
    status_code=status.HTTP_200_OK,
)
def queue_application(
    request: ApplicationQueueRequest,
    db: Session = Depends(get_db_session),
) -> APIResponse[ApplicationQueueResult]:
    """
    Evaluate one persisted job and queue it for application.
    """

    # --------------------------------------------------------------
    # 1. Validate job existence
    # --------------------------------------------------------------

    job_model = db.get(
        JobModel,
        request.job_id,
    )

    if job_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Job not found: {request.job_id}"
            ),
        )

    # --------------------------------------------------------------
    # 2. Validate job activity
    # --------------------------------------------------------------

    if not job_model.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The selected job is no longer active."
            ),
        )

    # --------------------------------------------------------------
    # 3. Build domain objects
    # --------------------------------------------------------------

    try:
        job = _job_model_to_domain(
            job_model
        )

        profile = _build_candidate_profile(
            request
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        ) from exc

    # --------------------------------------------------------------
    # 4. Application repository
    # --------------------------------------------------------------

    application_repository = (
        SQLAlchemyApplicationRepository(
            db
        )
    )

    # --------------------------------------------------------------
    # 5. Persistent duplicate protection
    # --------------------------------------------------------------

    existing_application = (
        application_repository.get_by_job(
            user_id=request.user_id,
            job_id=request.job_id,
            resume_id=request.resume_id,
        )
    )

    if existing_application is not None:

        existing_response = (
            ApplicationQueueResponse(
                application_id=(
                    existing_application.application_id
                ),
                user_id=request.user_id,
                job_id=request.job_id,
                resume_id=request.resume_id,
                resume_version_id=(
                    request.resume_version_id
                ),
                external_job_id=(
                    existing_application.external_job_id
                ),
                source=(
                    existing_application.source.value
                    if hasattr(
                        existing_application.source,
                        "value",
                    )
                    else str(
                        existing_application.source
                    )
                ),
                job_url=existing_application.job_url,
                job_title=(
                    existing_application.job_title
                ),
                company_name=(
                    existing_application.company_name
                ),
                match_score=(
                    existing_application.match_score
                ),
                status=existing_application.status,
                priority=(
                    existing_application.priority
                ),
                attempt_count=(
                    existing_application.attempt_count
                ),
                max_attempts=(
                    existing_application.max_attempts
                ),
                queued_at=(
                    existing_application.created_at
                ),
                metadata=dict(
                    existing_application.metadata
                ),
            )
        )

        result = ApplicationQueueResult(
            application=existing_response,
            queued=False,
            persisted=True,
            reason=(
                "An application already exists for "
                "this user, job, and resume."
            ),
            metadata={
                "duplicate": True,
            },
        )

        return APIResponse(
            success=True,
            data=result,
            message=(
                "Application already exists."
            ),
        )

    # --------------------------------------------------------------
    # 6. Application pipeline
    # --------------------------------------------------------------

    pipeline = ApplicationPipelineService(
        application_repository=(
            application_repository
        )
    )

    pipeline_result = pipeline.process_job(
        job,
        profile,
        user_id=request.user_id,
        job_id=request.job_id,
        resume_id=request.resume_id,
        resume_version_id=(
            request.resume_version_id
        ),
        priority=request.priority,
        metadata=dict(
            request.metadata
        ),
    )

    # --------------------------------------------------------------
    # 7. Handle non-queued result
    # --------------------------------------------------------------

    if not pipeline_result.queued:

        result = ApplicationQueueResult(
            application=(
                _queue_item_to_response(
                    queue_item=pipeline_result.queue_item,
                    request=request,
                )
                if pipeline_result.queue_item
                is not None
                else None
            ),
            queued=False,
            persisted=False,
            reason=pipeline_result.reason,
            metadata={
                **dict(
                    pipeline_result.metadata
                ),
                "match_score": (
                    pipeline_result
                    .match_result
                    .overall_score
                ),
                "match_decision": (
                    pipeline_result
                    .match_result
                    .decision
                ),
            },
        )

        return APIResponse(
            success=True,
            data=result,
            message=(
                "Application was not queued."
            ),
        )

    # --------------------------------------------------------------
    # 8. Ensure queue item exists
    # --------------------------------------------------------------

    if pipeline_result.queue_item is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Application was marked as queued, "
                "but no queue item was returned."
            ),
        )

    # --------------------------------------------------------------
    # 9. Return successful result
    # --------------------------------------------------------------

    response_application = (
        _queue_item_to_response(
            queue_item=pipeline_result.queue_item,
            request=request,
        )
    )

    result = ApplicationQueueResult(
        application=response_application,
        queued=True,
        persisted=pipeline_result.persisted,
        reason=pipeline_result.reason,
        metadata={
            **dict(
                pipeline_result.metadata
            ),
            "match_score": (
                pipeline_result
                .match_result
                .overall_score
            ),
            "match_decision": (
                pipeline_result
                .match_result
                .decision
            ),
            "eligibility_decision": (
                pipeline_result
                .eligibility_decision
                .value
                if hasattr(
                    pipeline_result
                    .eligibility_decision,
                    "value",
                )
                else str(
                    pipeline_result
                    .eligibility_decision
                )
            ),
        },
    )

    return APIResponse(
        success=True,
        data=result,
        message=(
            "Application successfully queued."
        ),
    )


__all__ = [
    "router",
]
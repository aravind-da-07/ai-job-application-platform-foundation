"""
Resume management API.

Provides API access to logical resumes, resume versions,
and resume file uploads.

The router intentionally contains no SQLAlchemy-specific business logic.
It delegates business operations to application services.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from src.api.schemas.resume import (
    CreateResumeRequest,
    ResumeResponse,
    ResumeUploadResponse,
    ResumeVersionResponse,
)
from src.modules.resumes.domain.repositories.resume_repository import (
    ResumeRepository,
)
from src.modules.resumes.infrastructure.repositories.resume_repository_impl import (
    SQLAlchemyResumeRepository,
)
from src.modules.resumes.services.resume_service import ResumeService
from src.modules.resumes.services.upload_service import UploadService
from src.shared.database.session import get_db_session
from src.shared.schemas.response_models import APIResponse
from src.shared.storage import SupabaseStorageAdapter


router = APIRouter(
    prefix="/resumes",
    tags=["resumes"],
)


def get_resume_service(
    db: Session = Depends(get_db_session),
) -> ResumeService:
    """
    Build the resume application service for the current request.
    """

    repository: ResumeRepository = SQLAlchemyResumeRepository(
        db
    )

    return ResumeService(
        repository
    )


def get_upload_service(
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> UploadService:
    """
    Build the resume upload application service.
    """

    storage = SupabaseStorageAdapter()

    return UploadService(
        resume_service=service,
        storage=storage,
    )


@router.post(
    "",
    response_model=APIResponse[ResumeResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_resume(
    request: CreateResumeRequest,
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> APIResponse[ResumeResponse]:
    """
    Create a new logical resume for a user.
    """

    resume = service.create_resume(
        user_id=request.user_id,
        name=request.name,
    )

    return APIResponse(
        success=True,
        data=ResumeResponse.model_validate(
            resume
        ),
        message="Resume created successfully.",
    )


@router.post(
    "/{resume_id}/upload",
    response_model=APIResponse[ResumeUploadResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_resume(
    resume_id: UUID,
    file: UploadFile = File(...),
    service: UploadService = Depends(
        get_upload_service
    ),
) -> APIResponse[ResumeUploadResponse]:
    """
    Upload a resume file and register it as a new resume version.
    """

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    resume = service.get_resume(
        resume_id
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume '{resume_id}' was not found.",
        )

    suffix = Path(
        file.filename
    ).suffix.lower()

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=suffix,
        ) as temporary_file:

            temporary_path = Path(
                temporary_file.name
            )

            while chunk := file.file.read(
                1024 * 1024
            ):
                temporary_file.write(
                    chunk
                )

        version = service.upload_resume(
            user_id=resume.user_id,
            resume_id=resume_id,
            file_path=temporary_path,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

    return APIResponse(
        success=True,
        data=ResumeUploadResponse(
            version=ResumeVersionResponse.model_validate(
                version
            ),
            message="Resume uploaded successfully.",
        ),
        message="Resume uploaded successfully.",
    )


@router.get(
    "/{resume_id}",
    response_model=APIResponse[ResumeResponse],
)
def get_resume(
    resume_id: UUID,
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> APIResponse[ResumeResponse]:
    """
    Retrieve a logical resume.
    """

    resume = service.get_resume(
        resume_id
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume '{resume_id}' was not found.",
        )

    return APIResponse(
        success=True,
        data=ResumeResponse.model_validate(
            resume
        ),
    )


@router.get(
    "/user/{user_id}",
    response_model=APIResponse[list[ResumeResponse]],
)
def get_user_resumes(
    user_id: UUID,
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> APIResponse[list[ResumeResponse]]:
    """
    Retrieve all logical resumes belonging to a user.
    """

    resumes = service.get_user_resumes(
        user_id
    )

    return APIResponse(
        success=True,
        data=[
            ResumeResponse.model_validate(
                resume
            )
            for resume in resumes
        ],
    )


@router.get(
    "/{resume_id}/versions",
    response_model=APIResponse[list[ResumeVersionResponse]],
)
def list_resume_versions(
    resume_id: UUID,
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> APIResponse[list[ResumeVersionResponse]]:
    """
    Retrieve all versions belonging to a logical resume.
    """

    resume = service.get_resume(
        resume_id
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume '{resume_id}' was not found.",
        )

    versions = service.list_versions(
        resume_id
    )

    return APIResponse(
        success=True,
        data=[
            ResumeVersionResponse.model_validate(
                version
            )
            for version in versions
        ],
    )


@router.get(
    "/{resume_id}/active-version",
    response_model=APIResponse[
        ResumeVersionResponse | None
    ],
)
def get_active_resume_version(
    resume_id: UUID,
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> APIResponse[
    ResumeVersionResponse | None
]:
    """
    Retrieve the currently active version of a resume.
    """

    resume = service.get_resume(
        resume_id
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume '{resume_id}' was not found.",
        )

    version = service.get_active_version(
        resume_id
    )

    return APIResponse(
        success=True,
        data=(
            ResumeVersionResponse.model_validate(
                version
            )
            if version is not None
            else None
        ),
    )


@router.get(
    "/version/{version_id}",
    response_model=APIResponse[ResumeVersionResponse],
)
def get_resume_version(
    version_id: UUID,
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> APIResponse[ResumeVersionResponse]:
    """
    Retrieve a specific resume version.
    """

    version = service.get_version(
        version_id
    )

    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume version '{version_id}' was not found.",
        )

    return APIResponse(
        success=True,
        data=ResumeVersionResponse.model_validate(
            version
        ),
    )


@router.post(
    "/version/{version_id}/activate",
    response_model=APIResponse[ResumeVersionResponse],
)
def activate_resume_version(
    version_id: UUID,
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> APIResponse[ResumeVersionResponse]:
    """
    Activate an existing resume version.
    """

    try:
        version = service.activate_version(
            version_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return APIResponse(
        success=True,
        data=ResumeVersionResponse.model_validate(
            version
        ),
        message="Resume version activated successfully.",
    )


@router.patch(
    "/{resume_id}/archive",
    response_model=APIResponse[ResumeResponse],
)
def archive_resume(
    resume_id: UUID,
    service: ResumeService = Depends(
        get_resume_service
    ),
) -> APIResponse[ResumeResponse]:
    """
    Archive a logical resume.
    """

    try:
        resume = service.archive_resume(
            resume_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return APIResponse(
        success=True,
        data=ResumeResponse.model_validate(
            resume
        ),
        message="Resume archived successfully.",
    )


__all__ = ["router"]
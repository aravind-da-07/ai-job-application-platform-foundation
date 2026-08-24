"""
User management API.

The router is intentionally thin.

Business logic is delegated to UserService.
Persistence is delegated to UserRepository.
SQLAlchemy-specific logic remains in the infrastructure layer.
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

from src.api.schemas.users import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
)
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.modules.users.services.user_service import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserService,
)
from src.shared.database.session import get_db_session
from src.shared.schemas.response_models import APIResponse


router = APIRouter(
    prefix="/users",
    tags=["users"],
)


def get_user_service(
    db: Session = Depends(get_db_session),
) -> UserService:
    """
    Build the UserService for the current request.
    """

    repository = SQLAlchemyUserRepository(
        db
    )

    return UserService(
        repository
    )


# ---------------------------------------------------------------------------
# Create user
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    request: CreateUserRequest,
    service: UserService = Depends(
        get_user_service
    ),
) -> APIResponse[UserResponse]:
    """
    Create a new platform user.
    """

    try:
        user = service.create_user(
            full_name=request.full_name,
            email=request.email,
            phone=request.phone,
        )

    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return APIResponse(
        success=True,
        data=UserResponse.model_validate(
            user
        ),
        message="User created successfully.",
    )


# ---------------------------------------------------------------------------
# Get user
# ---------------------------------------------------------------------------


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
)
def get_user(
    user_id: UUID,
    service: UserService = Depends(
        get_user_service
    ),
) -> APIResponse[UserResponse]:
    """
    Retrieve a user by UUID.
    """

    try:
        user = service.get_user_by_id(
            user_id
        )

    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return APIResponse(
        success=True,
        data=UserResponse.model_validate(
            user
        ),
        message="User retrieved successfully.",
    )


# ---------------------------------------------------------------------------
# List users
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=APIResponse[list[UserResponse]],
)
def list_users(
    active_only: bool = False,
    service: UserService = Depends(
        get_user_service
    ),
) -> APIResponse[list[UserResponse]]:
    """
    Retrieve users.

    By default all users are returned.
    Set active_only=true to return active users only.
    """

    users = service.list_users(
        active_only=active_only
    )

    return APIResponse(
        success=True,
        data=[
            UserResponse.model_validate(
                user
            )
            for user in users
        ],
        message="Users retrieved successfully.",
    )


# ---------------------------------------------------------------------------
# Update user
# ---------------------------------------------------------------------------


@router.patch(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
)
def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    service: UserService = Depends(
        get_user_service
    ),
) -> APIResponse[UserResponse]:
    """
    Update an existing user.
    """

    try:
        user = service.update_user(
            user_id=user_id,
            full_name=request.full_name,
            email=request.email,
            phone=request.phone,
            email_verified=request.email_verified,
            is_active=request.is_active,
        )

    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return APIResponse(
        success=True,
        data=UserResponse.model_validate(
            user
        ),
        message="User updated successfully.",
    )


# ---------------------------------------------------------------------------
# Deactivate user
# ---------------------------------------------------------------------------


@router.patch(
    "/{user_id}/deactivate",
    response_model=APIResponse[UserResponse],
)
def deactivate_user(
    user_id: UUID,
    service: UserService = Depends(
        get_user_service
    ),
) -> APIResponse[UserResponse]:
    """
    Deactivate a user without deleting the record.
    """

    try:
        user = service.deactivate_user(
            user_id
        )

    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return APIResponse(
        success=True,
        data=UserResponse.model_validate(
            user
        ),
        message="User deactivated successfully.",
    )


__all__ = [
    "router",
]
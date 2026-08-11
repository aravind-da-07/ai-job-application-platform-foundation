"""
Application service for user management.

The UserService contains application/business rules for users.
It depends on the domain repository contract rather than directly
depending on SQLAlchemy or PostgreSQL.
"""

from __future__ import annotations

from uuid import UUID

from src.modules.users.domain.entities.user import User
from src.modules.users.domain.repositories.user_repository import (
    UserRepository,
)


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an existing email."""


class UserNotFoundError(Exception):
    """Raised when a requested user does not exist."""


class UserService:
    """
    Application service responsible for user-related business operations.
    """

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    @staticmethod
    def _normalize_email(email: str) -> str:
        """
        Normalize an email address before persistence.

        Leading/trailing whitespace is removed and the address is
        converted to lowercase.
        """

        return email.strip().lower()

    def create_user(
        self,
        *,
        full_name: str,
        email: str,
        phone: str | None = None,
    ) -> User:
        """
        Create a new user.

        Business rules:
        1. Normalize the email.
        2. Check whether the email already exists.
        3. Create the domain User entity.
        4. Persist it through the repository.
        """

        normalized_email = self._normalize_email(email)

        existing_user = self._repository.get_by_email(
            normalized_email
        )

        if existing_user is not None:
            raise UserAlreadyExistsError(
                f"A user with email '{normalized_email}' already exists."
            )

        user = User(
            full_name=full_name.strip(),
            email=normalized_email,
            phone=phone,
        )

        return self._repository.create(user)

    def get_user_by_id(self, user_id: UUID) -> User:
        """
        Retrieve a user by ID.

        Raises:
            UserNotFoundError: If the user does not exist.
        """

        user = self._repository.get_by_id(user_id)

        if user is None:
            raise UserNotFoundError(
                f"User with id '{user_id}' was not found."
            )

        return user

    def get_user_by_email(self, email: str) -> User:
        """
        Retrieve a user by email.

        The email is normalized before lookup.

        Raises:
            UserNotFoundError: If the user does not exist.
        """

        normalized_email = self._normalize_email(email)

        user = self._repository.get_by_email(
            normalized_email
        )

        if user is None:
            raise UserNotFoundError(
                f"User with email '{normalized_email}' was not found."
            )

        return user

    def list_users(
        self,
        *,
        active_only: bool = False,
    ) -> list[User]:
        """
        Return users, optionally limited to active users.
        """

        return self._repository.list_users(
            active_only=active_only
        )

    def update_user(
        self,
        user_id: UUID,
        *,
        full_name: str,
        email: str,
        phone: str | None = None,
        email_verified: bool = False,
        is_active: bool = True,
    ) -> User:
        """
        Update an existing user.

        Business rules:
        1. Confirm the user exists.
        2. Normalize the email.
        3. Prevent the email from belonging to another user.
        4. Build a new immutable domain entity.
        5. Persist the updated entity.
        """

        existing_user = self.get_user_by_id(user_id)

        normalized_email = self._normalize_email(email)

        user_with_email = self._repository.get_by_email(
            normalized_email
        )

        if (
            user_with_email is not None
            and user_with_email.id != existing_user.id
        ):
            raise UserAlreadyExistsError(
                f"A different user already uses email "
                f"'{normalized_email}'."
            )

        updated_user = User(
            id=existing_user.id,
            full_name=full_name.strip(),
            email=normalized_email,
            phone=phone,
            auth_provider=existing_user.auth_provider,
            is_active=is_active,
            email_verified=email_verified,
        )

        return self._repository.update(updated_user)

    def deactivate_user(self, user_id: UUID) -> User:
        """
        Deactivate a user without physically deleting the database record.
        """

        existing_user = self.get_user_by_id(user_id)

        deactivated_user = User(
            id=existing_user.id,
            full_name=existing_user.full_name,
            email=existing_user.email,
            phone=existing_user.phone,
            auth_provider=existing_user.auth_provider,
            is_active=False,
            email_verified=existing_user.email_verified,
        )

        return self._repository.update(deactivated_user)

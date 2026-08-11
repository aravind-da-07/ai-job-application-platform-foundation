"""
Domain repository contract for users.

This module defines what the user domain needs from persistence.

It does not contain SQLAlchemy, PostgreSQL, Supabase, or other
infrastructure-specific implementation details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.users.domain.entities.user import User


class UserRepository(ABC):
    """
    Abstract repository contract for User persistence.

    The domain layer defines the operations it needs.
    The infrastructure layer provides the actual implementation.
    """

    @abstractmethod
    def create(self, user: User) -> User:
        """
        Persist a new user.

        Args:
            user: Domain User entity to persist.

        Returns:
            The persisted User entity.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> User | None:
        """
        Retrieve a user by UUID.

        Args:
            user_id: Unique user identifier.

        Returns:
            User if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """
        Retrieve a user by email address.

        Args:
            email: User email address.

        Returns:
            User if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def list_users(
        self,
        *,
        active_only: bool = False,
    ) -> list[User]:
        """
        Retrieve users.

        Args:
            active_only: If True, return only active users.

        Returns:
            List of User domain entities.
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, user: User) -> User:
        """
        Update an existing user.

        Args:
            user: Updated User domain entity.

        Returns:
            Updated User entity.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: UUID) -> None:
        """
        Delete a user.

        Args:
            user_id: Unique user identifier.
        """
        raise NotImplementedError
"""
SQLAlchemy implementation of the UserRepository contract.

This module is responsible only for persistence operations.
Business rules belong in the service/domain layer.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.users.domain.entities.user import User
from src.modules.users.domain.repositories.user_repository import (
    UserRepository,
)
from src.modules.users.infrastructure.models.user_model import UserModel


class SQLAlchemyUserRepository(UserRepository):
    """
    PostgreSQL/SQLAlchemy implementation of UserRepository.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, user: User) -> User:
        """
        Persist a new domain User entity.
        """

        model = UserModel(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            auth_provider=user.auth_provider,
            is_active=user.is_active,
            email_verified=user.email_verified,
        )

        self._session.add(model)
        self._session.flush()

        return self._to_domain(model)

    def get_by_id(self, user_id: UUID) -> User | None:
        """
        Retrieve a user by UUID.
        """

        statement = select(UserModel).where(
            UserModel.id == user_id
        )

        model = self._session.scalar(statement)

        if model is None:
            return None

        return self._to_domain(model)

    def get_by_email(self, email: str) -> User | None:
        """
        Retrieve a user by email address.
        """

        statement = select(UserModel).where(
            UserModel.email == email
        )

        model = self._session.scalar(statement)

        if model is None:
            return None

        return self._to_domain(model)

    def list_users(
        self,
        *,
        active_only: bool = False,
    ) -> list[User]:
        """
        Retrieve users from the database.
        """

        statement = select(UserModel).order_by(
            UserModel.created_at.desc()
        )

        if active_only:
            statement = statement.where(
                UserModel.is_active.is_(True)
            )

        models = self._session.scalars(statement).all()

        return [
            self._to_domain(model)
            for model in models
        ]

    def update(self, user: User) -> User:
        """
        Update an existing user.
        """

        model = self._session.get(UserModel, user.id)

        if model is None:
            raise ValueError(
                f"User with id {user.id} was not found."
            )

        model.full_name = user.full_name
        model.email = user.email
        model.phone = user.phone
        model.auth_provider = user.auth_provider
        model.is_active = user.is_active
        model.email_verified = user.email_verified

        self._session.flush()

        return self._to_domain(model)

    def delete(self, user_id: UUID) -> None:
        """
        Delete a user record.

        NOTE:
        The application will normally prefer deactivation
        (`is_active=False`) to preserve audit history.
        """

        model = self._session.get(UserModel, user_id)

        if model is not None:
            self._session.delete(model)
            self._session.flush()

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        """
        Convert SQLAlchemy ORM model to domain entity.
        """

        return User(
            id=model.id,
            full_name=model.full_name,
            email=model.email,
            phone=model.phone,
            auth_provider=model.auth_provider,
            is_active=model.is_active,
            email_verified=model.email_verified,
        )
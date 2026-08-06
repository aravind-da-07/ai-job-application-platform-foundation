"""
Generic base repository.

Repositories are the ONLY layer permitted to touch the SQLAlchemy
`Session` directly. They contain no business logic — only persistence
operations (create, read, update, delete, list, count). Business logic
belongs in the service layer, which composes one or more repositories.

Every concrete repository should subclass `BaseRepository[ModelType]`
and add domain-specific query methods (e.g. `get_by_email`), while
inheriting the generic CRUD operations for free.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.shared.core.exceptions import RecordNotFoundError
from src.shared.database.base import Base
from src.shared.logging.logger import get_logger

ModelType = TypeVar("ModelType", bound=Base)

logger = get_logger(__name__)


class BaseRepository(Generic[ModelType]):
    """Generic CRUD repository parameterized over a single ORM model type."""

    model: Type[ModelType]

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **fields: Any) -> ModelType:
        instance = self.model(**fields)
        self.session.add(instance)
        self.session.flush()  # populate defaults (id, timestamps) without ending the transaction
        return instance

    def get_by_id(self, record_id: uuid.UUID) -> ModelType:
        instance = self.session.get(self.model, record_id)
        if instance is None:
            raise RecordNotFoundError(
                f"{self.model.__name__} with id={record_id} was not found"
            )
        return instance

    def try_get_by_id(self, record_id: uuid.UUID) -> ModelType | None:
        return self.session.get(self.model, record_id)

    def list(self, *, limit: int = 100, offset: int = 0, **filters: Any) -> Sequence[ModelType]:
        stmt = select(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        stmt = stmt.limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        return self.session.execute(stmt).scalar_one()

    def update(self, record_id: uuid.UUID, **fields: Any) -> ModelType:
        instance = self.get_by_id(record_id)
        for field, value in fields.items():
            setattr(instance, field, value)
        self.session.flush()
        return instance

    def delete(self, record_id: uuid.UUID) -> None:
        instance = self.get_by_id(record_id)
        self.session.delete(instance)
        self.session.flush()

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.shared.core.exceptions import RecordNotFoundError
from src.shared.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.shared.repositories.base_repository import BaseRepository


class _Widget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "test_widgets"
    name: Mapped[str] = mapped_column()


class _WidgetRepository(BaseRepository[_Widget]):
    model = _Widget


@pytest.fixture()
def repo(db_session: Session) -> _WidgetRepository:
    return _WidgetRepository(db_session)


def test_create_and_get_by_id(repo: _WidgetRepository) -> None:
    widget = repo.create(name="alpha")
    assert widget.id is not None
    assert widget.created_at is not None

    fetched = repo.get_by_id(widget.id)
    assert fetched.name == "alpha"


def test_get_by_id_raises_when_missing(repo: _WidgetRepository) -> None:
    with pytest.raises(RecordNotFoundError):
        repo.get_by_id(uuid.uuid4())


def test_update(repo: _WidgetRepository) -> None:
    widget = repo.create(name="beta")
    updated = repo.update(widget.id, name="beta-renamed")
    assert updated.name == "beta-renamed"


def test_list_and_count_with_filters(repo: _WidgetRepository) -> None:
    repo.create(name="dup")
    repo.create(name="dup")
    repo.create(name="unique")

    assert repo.count(name="dup") == 2
    assert len(repo.list(name="dup")) == 2


def test_delete(repo: _WidgetRepository) -> None:
    widget = repo.create(name="gamma")
    repo.delete(widget.id)
    with pytest.raises(RecordNotFoundError):
        repo.get_by_id(widget.id)

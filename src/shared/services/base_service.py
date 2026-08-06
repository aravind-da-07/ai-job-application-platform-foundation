"""
Base service class.

Services hold business logic and orchestrate one or more repositories.
Controllers/API routers must depend on services, never on repositories
or the database session directly — this keeps the API layer thin and
the business rules testable in isolation from HTTP.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.shared.logging.logger import get_logger


class BaseService:
    """
    Marker/convenience base class. Concrete services accept a `Session`
    (typically injected via FastAPI's `Depends(get_db_session)`) and
    construct whichever repositories they need from it.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.logger = get_logger(self.__class__.__module__)

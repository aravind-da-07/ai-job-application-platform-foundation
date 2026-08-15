"""
FastAPI application entry point.

Run locally with:
    uvicorn src.api.main:app --reload --port 8000

This module wires together settings, logging, middleware,
error handlers, and API routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import jobs
from src.api.routers import resumes
from src.api.routers import system
from src.shared.config.settings import get_settings
from src.shared.logging.logger import configure_logging, get_logger
from src.shared.middleware.error_handlers import register_error_handlers
from src.shared.middleware.request_logging import RequestLoggingMiddleware
from src.shared.scheduler.scheduler_manager import get_scheduler_manager


configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    """

    settings = get_settings()

    logger.info(
        "Starting {} v{} [{}]",
        settings.app_name,
        settings.app_version,
        settings.environment.value,
    )

    scheduler = get_scheduler_manager()
    scheduler.start()

    yield

    logger.info(
        "Shutting down {}",
        settings.app_name,
    )

    scheduler.shutdown(
        wait=True
    )


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI Job Application Platform — automates resume parsing, "
            "job discovery, AI matching, and supported application "
            "submission."
        ),
        lifespan=lifespan,
    )

    # --------------------------------------------------------------
    # Middleware
    # --------------------------------------------------------------

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        RequestLoggingMiddleware
    )

    # --------------------------------------------------------------
    # Error handlers
    # --------------------------------------------------------------

    register_error_handlers(
        app
    )

    # --------------------------------------------------------------
    # API routers
    # --------------------------------------------------------------

    app.include_router(
        system.router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        resumes.router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        jobs.router,
        prefix=settings.api_prefix,
    )

    return app


app = create_app()
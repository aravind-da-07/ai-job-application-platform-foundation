"""
Centralized FastAPI exception handling.

Every PlatformError subclass is caught here, logged with full context,
and translated into a consistent ErrorResponse — never a raw stack
trace to the client. Unexpected (non-platform) exceptions are logged
at ERROR with the traceback and returned as a generic 500 so internals
are never leaked.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.shared.core.exceptions import PlatformError
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlatformError)
    async def handle_platform_error(request: Request, exc: PlatformError) -> JSONResponse:
        logger.warning(
            "Handled PlatformError on {} {}: {} ({})",
            request.method,
            request.url.path,
            exc.message,
            exc.code,
        )
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception on {} {}", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "internal_server_error",
                "message": "An unexpected error occurred.",
                "details": {},
            },
        )

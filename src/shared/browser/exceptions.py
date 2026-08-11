"""
Browser-specific exceptions.

These exceptions extend the platform automation hierarchy so callers can
handle browser failures without depending directly on Playwright's
exception classes.
"""

from __future__ import annotations

from typing import Any, Optional

from src.shared.core.exceptions import AutomationError


class BrowserError(AutomationError):
    """Base exception for browser-engine failures."""

    code = "browser_error"
    http_status = 500


class BrowserConfigurationError(BrowserError):
    """Raised when browser configuration is invalid."""

    code = "browser_configuration_error"
    http_status = 500


class BrowserLaunchError(BrowserError):
    """Raised when the browser cannot be launched."""

    code = "browser_launch_error"
    http_status = 503


class BrowserContextError(BrowserError):
    """Raised when a browser context cannot be created or managed."""

    code = "browser_context_error"
    http_status = 500


class BrowserNavigationError(BrowserError):
    """Raised when browser navigation fails."""

    code = "browser_navigation_error"
    http_status = 502


class BrowserPageError(BrowserError):
    """Raised when browser page operations fail."""

    code = "browser_page_error"
    http_status = 500


class BrowserClosedError(BrowserError):
    """Raised when an operation is attempted after browser shutdown."""

    code = "browser_closed"
    http_status = 409
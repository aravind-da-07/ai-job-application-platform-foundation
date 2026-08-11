"""
Browser automation configuration.

This module translates application Settings into strongly typed browser
configuration used by the Playwright browser engine.

Browser-specific values are never hardcoded here. They come from the
centralized application settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.shared.config.settings import get_settings
from src.shared.core.exceptions import ConfigurationError


class BrowserType(str, Enum):
    """Supported Playwright browser engines."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


@dataclass(frozen=True)
class BrowserConfig:
    """
    Immutable configuration for one Playwright browser session.
    """

    browser_type: BrowserType
    headless: bool
    slow_mo_ms: int
    navigation_timeout_ms: int
    sessions_dir: str

    @classmethod
    def from_settings(cls) -> BrowserConfig:
        """
        Build browser configuration from centralized application settings.
        """

        settings = get_settings()

        try:
            browser_type = BrowserType(
                settings.browser_type.strip().lower()
            )
        except ValueError as exc:
            raise ConfigurationError(
                f"Unsupported browser type: '{settings.browser_type}'. "
                f"Supported values are: "
                f"{', '.join(browser.value for browser in BrowserType)}."
            ) from exc

        if settings.browser_slow_mo_ms < 0:
            raise ConfigurationError(
                "browser_slow_mo_ms cannot be negative."
            )

        if settings.browser_navigation_timeout_ms <= 0:
            raise ConfigurationError(
                "browser_navigation_timeout_ms must be greater than zero."
            )

        sessions_dir = settings.browser_sessions_dir.strip()

        if not sessions_dir:
            raise ConfigurationError(
                "browser_sessions_dir cannot be empty."
            )

        return cls(
            browser_type=browser_type,
            headless=settings.browser_headless,
            slow_mo_ms=settings.browser_slow_mo_ms,
            navigation_timeout_ms=settings.browser_navigation_timeout_ms,
            sessions_dir=sessions_dir,
        )
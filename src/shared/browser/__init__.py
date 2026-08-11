"""
Shared browser automation package.

Exports the public browser infrastructure used by the platform.
"""

from __future__ import annotations

from src.shared.browser.browser_config import (
    BrowserConfig,
    BrowserType,
)
from src.shared.browser.browser_engine import (
    BrowserEngine,
)
from src.shared.browser.exceptions import (
    BrowserClosedError,
    BrowserContextError,
    BrowserLaunchError,
    BrowserNavigationError,
    BrowserPageError,
)

__all__ = [
    "BrowserConfig",
    "BrowserType",
    "BrowserEngine",
    "BrowserClosedError",
    "BrowserContextError",
    "BrowserLaunchError",
    "BrowserNavigationError",
    "BrowserPageError",
]
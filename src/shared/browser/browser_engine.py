"""
Shared Playwright browser automation engine.

This module provides the low-level browser infrastructure used by the
automation system.

Responsibilities:
- Start and stop Playwright.
- Launch the configured browser.
- Create isolated browser contexts.
- Create pages.
- Configure browser timeouts.
- Navigate pages.
- Capture screenshots.
- Start and stop Playwright tracing.
- Provide safe lifecycle management.

Portal-specific business logic must NOT be implemented here.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from src.shared.browser.browser_config import (
    BrowserConfig,
    BrowserType,
)
from src.shared.browser.exceptions import (
    BrowserClosedError,
    BrowserContextError,
    BrowserLaunchError,
    BrowserNavigationError,
    BrowserPageError,
)
from src.shared.logging.logger import get_logger


logger = get_logger(__name__)


class BrowserEngine:
    """
    Shared synchronous Playwright browser engine.

    The engine owns:
        - one Playwright instance
        - one browser instance

    Each automation execution should normally create its own
    BrowserContext so that sessions remain isolated.
    """

    def __init__(
        self,
        config: BrowserConfig | None = None,
    ) -> None:
        self.config = config or BrowserConfig.from_settings()

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._closed = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        """
        Return True when the browser engine is active.
        """

        return (
            not self._closed
            and self._playwright is not None
            and self._browser is not None
            and self._browser.is_connected()
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Start Playwright and launch the configured browser.

        Calling start() multiple times while the engine is already
        running is safe.
        """

        if self.running:
            return

        if self._closed:
            raise BrowserClosedError(
                "BrowserEngine has already been closed and cannot be "
                "restarted."
            )

        try:
            self._playwright = sync_playwright().start()

            launcher = self._get_browser_launcher()

            self._browser = launcher.launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo_ms,
            )

            logger.info(
                "Browser engine started: type={}, headless={}",
                self.config.browser_type.value,
                self.config.headless,
            )

        except BrowserClosedError:
            raise

        except Exception as exc:
            self._cleanup_failed_start()

            raise BrowserLaunchError(
                "Failed to launch "
                f"{self.config.browser_type.value} browser: {exc}"
            ) from exc

    def shutdown(self) -> None:
        """
        Shut down the browser engine.

        Shutdown is idempotent. Calling it multiple times is safe.
        """

        browser = self._browser
        playwright = self._playwright

        self._browser = None
        self._playwright = None
        self._closed = True

        if browser is not None:
            try:
                browser.close()
            except Exception:
                logger.exception(
                    "Failed to close Playwright browser cleanly."
                )

        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                logger.exception(
                    "Failed to stop Playwright cleanly."
                )

        logger.info("Browser engine shut down.")

    def __enter__(self) -> BrowserEngine:
        """
        Start the engine when entering a context manager.
        """

        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        """
        Shut down the engine when leaving a context manager.
        """

        self.shutdown()

    # ------------------------------------------------------------------
    # Internal requirements
    # ------------------------------------------------------------------

    def _require_browser(self) -> Browser:
        """
        Return the active browser.

        Raises:
            BrowserClosedError: if the engine is not running.
        """

        if not self.running or self._browser is None:
            raise BrowserClosedError(
                "Browser engine is not running. "
                "Call start() before using the browser."
            )

        return self._browser

    def _require_playwright(self) -> Playwright:
        """
        Return the active Playwright instance.
        """

        if self._playwright is None or self._closed:
            raise BrowserClosedError(
                "Playwright is not running."
            )

        return self._playwright

    def _get_browser_launcher(self):
        """
        Return the Playwright browser launcher selected by configuration.
        """

        playwright = self._require_playwright()

        if self.config.browser_type == BrowserType.CHROMIUM:
            return playwright.chromium

        if self.config.browser_type == BrowserType.FIREFOX:
            return playwright.firefox

        if self.config.browser_type == BrowserType.WEBKIT:
            return playwright.webkit

        raise BrowserLaunchError(
            "Unsupported browser type: "
            f"{self.config.browser_type.value}"
        )

    def _cleanup_failed_start(self) -> None:
        """
        Clean up resources if browser startup partially fails.
        """

        browser = self._browser
        playwright = self._playwright

        self._browser = None
        self._playwright = None

        if browser is not None:
            try:
                browser.close()
            except Exception:
                logger.exception(
                    "Failed to clean up partially started browser."
                )

        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                logger.exception(
                    "Failed to clean up partially started Playwright."
                )

    # ------------------------------------------------------------------
    # Browser contexts
    # ------------------------------------------------------------------

    def create_context(
        self,
        *,
        storage_state: str | Path | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
        user_agent: str | None = None,
    ) -> BrowserContext:
        """
        Create an isolated browser context.

        storage_state can be used later for authenticated portal sessions.
        """

        browser = self._require_browser()

        try:
            context_options: dict[str, object] = {}

            if storage_state is not None:
                context_options["storage_state"] = str(
                    storage_state
                )

            if locale is not None:
                context_options["locale"] = locale

            if timezone_id is not None:
                context_options["timezone_id"] = timezone_id

            if user_agent is not None:
                context_options["user_agent"] = user_agent

            context = browser.new_context(
                **context_options
            )

            context.set_default_timeout(
                self.config.navigation_timeout_ms
            )

            context.set_default_navigation_timeout(
                self.config.navigation_timeout_ms
            )

            logger.debug(
                "Created isolated browser context."
            )

            return context

        except Exception as exc:
            raise BrowserContextError(
                f"Failed to create browser context: {exc}"
            ) from exc

    @contextmanager
    def isolated_context(
        self,
        *,
        storage_state: str | Path | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
        user_agent: str | None = None,
    ) -> Iterator[BrowserContext]:
        """
        Create and automatically close an isolated browser context.
        """

        context = self.create_context(
            storage_state=storage_state,
            locale=locale,
            timezone_id=timezone_id,
            user_agent=user_agent,
        )

        try:
            yield context
        finally:
            try:
                context.close()
            except Exception:
                logger.exception(
                    "Failed to close browser context cleanly."
                )

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def new_page(
        self,
        context: BrowserContext,
    ) -> Page:
        """
        Create a new page inside a browser context.
        """

        if context is None:
            raise BrowserContextError(
                "A valid browser context is required."
            )

        try:
            page = context.new_page()

            page.set_default_timeout(
                self.config.navigation_timeout_ms
            )

            page.set_default_navigation_timeout(
                self.config.navigation_timeout_ms
            )

            logger.debug(
                "Created browser page."
            )

            return page

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to create browser page: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(
        self,
        page: Page,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> None:
        """
        Navigate a page to a URL.

        Portal-specific navigation logic belongs in portal connectors.
        """

        if page is None:
            raise BrowserPageError(
                "A valid Playwright page is required."
            )

        normalized_url = url.strip()

        if not normalized_url:
            raise BrowserNavigationError(
                "Navigation URL cannot be empty."
            )

        try:
            page.goto(
                normalized_url,
                wait_until=wait_until,
                timeout=self.config.navigation_timeout_ms,
            )

            logger.debug(
                "Navigated browser page to {}",
                normalized_url,
            )

        except PlaywrightTimeoutError as exc:
            raise BrowserNavigationError(
                "Navigation timed out after "
                f"{self.config.navigation_timeout_ms} ms: "
                f"{normalized_url}"
            ) from exc

        except Exception as exc:
            raise BrowserNavigationError(
                f"Failed to navigate to '{normalized_url}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def screenshot(
        self,
        page: Page,
        *,
        name: str,
        full_page: bool = True,
    ) -> Path:
        """
        Capture a screenshot into the configured browser session folder.
        """

        if page is None:
            raise BrowserPageError(
                "A valid Playwright page is required."
            )

        normalized_name = name.strip()

        if not normalized_name:
            raise BrowserPageError(
                "Screenshot name cannot be empty."
            )

        if not normalized_name.lower().endswith(".png"):
            normalized_name = (
                f"{normalized_name}.png"
            )

        output_directory = Path(
            self.config.sessions_dir
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = output_directory / normalized_name

        try:
            page.screenshot(
                path=str(output_path),
                full_page=full_page,
            )

            logger.debug(
                "Browser screenshot captured: {}",
                output_path,
            )

            return output_path

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to capture screenshot: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Tracing
    # ------------------------------------------------------------------

    def start_tracing(
        self,
        context: BrowserContext,
        *,
        screenshots: bool = True,
        snapshots: bool = True,
        sources: bool = True,
    ) -> None:
        """
        Start Playwright tracing for a browser context.
        """

        if context is None:
            raise BrowserContextError(
                "A valid browser context is required."
            )

        try:
            context.tracing.start(
                screenshots=screenshots,
                snapshots=snapshots,
                sources=sources,
            )

            logger.debug(
                "Browser tracing started."
            )

        except Exception as exc:
            raise BrowserContextError(
                f"Failed to start browser tracing: {exc}"
            ) from exc

    def stop_tracing(
        self,
        context: BrowserContext,
        *,
        name: str,
    ) -> Path:
        """
        Stop tracing and save the trace archive.
        """

        if context is None:
            raise BrowserContextError(
                "A valid browser context is required."
            )

        normalized_name = name.strip()

        if not normalized_name:
            raise BrowserContextError(
                "Trace name cannot be empty."
            )

        if not normalized_name.lower().endswith(".zip"):
            normalized_name = (
                f"{normalized_name}.zip"
            )

        output_directory = Path(
            self.config.sessions_dir
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = output_directory / normalized_name

        try:
            context.tracing.stop(
                path=str(output_path)
            )

            logger.debug(
                "Browser tracing stopped: {}",
                output_path,
            )

            return output_path

        except Exception as exc:
            raise BrowserContextError(
                f"Failed to stop browser tracing: {exc}"
            ) from exc
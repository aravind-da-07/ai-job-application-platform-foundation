"""
Playwright implementation of the job-discovery PortalSession contract.

This module is the infrastructure bridge between:

    JobPortal / PortalSession
            |
            v
    PlaywrightPortalSession
            |
            v
       BrowserEngine
            |
            v
         Playwright

The domain layer never imports Playwright directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Page

from src.modules.job_discovery.domain.ports.job_portal import (
    PortalSession,
)
from src.shared.browser import BrowserEngine
from src.shared.browser.exceptions import (
    BrowserContextError,
    BrowserPageError,
)


class PlaywrightPortalSession:
    """
    Concrete PortalSession implementation backed by Playwright.

    The class manages one isolated BrowserContext and one active Page.

    BrowserEngine remains responsible for:

        - starting Playwright
        - launching the browser
        - creating contexts
        - creating pages
        - navigation
        - browser lifecycle
    """

    def __init__(
        self,
        engine: BrowserEngine,
        *,
        storage_state: str | Path | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if engine is None:
            raise ValueError(
                "A BrowserEngine instance is required."
            )

        self.engine = engine
        self.storage_state = storage_state
        self.locale = locale
        self.timezone_id = timezone_id
        self.user_agent = user_agent

        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._closed = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        """
        Return True when the portal session has an active page.
        """

        return (
            not self._closed
            and self._context is not None
            and self._page is not None
            and not self._page.is_closed()
        )

    @property
    def context(self) -> BrowserContext:
        """
        Return the active Playwright browser context.
        """

        if self._context is None or self._closed:
            raise BrowserContextError(
                "Portal session is not open."
            )

        return self._context

    @property
    def page(self) -> Page:
        """
        Return the active Playwright page.
        """

        if (
            self._page is None
            or self._closed
            or self._page.is_closed()
        ):
            raise BrowserPageError(
                "Portal session does not have an active page."
            )

        return self._page

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Create an isolated browser context and page.

        BrowserEngine must already be running.
        """

        if self.running:
            return

        if self._closed:
            raise BrowserContextError(
                "Portal session has already been closed "
                "and cannot be restarted."
            )

        if not self.engine.running:
            raise BrowserContextError(
                "BrowserEngine is not running. "
                "Call engine.start() before starting the portal session."
            )

        try:
            self._context = self.engine.create_context(
                storage_state=self.storage_state,
                locale=self.locale,
                timezone_id=self.timezone_id,
                user_agent=self.user_agent,
            )

            self._page = self.engine.new_page(
                self._context
            )

        except Exception:
            self._cleanup_failed_start()
            raise

    def close(self) -> None:
        """
        Close the portal session.

        BrowserEngine is intentionally NOT shut down here.
        """

        page = self._page
        context = self._context

        self._page = None
        self._context = None
        self._closed = True

        if page is not None:
            try:
                if not page.is_closed():
                    page.close()
            except Exception:
                pass

        if context is not None:
            try:
                context.close()
            except Exception:
                pass

    def __enter__(self) -> PlaywrightPortalSession:
        """
        Start the portal session.
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
        Close the portal session.
        """

        self.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cleanup_failed_start(self) -> None:
        """
        Clean up partially-created Playwright resources.
        """

        page = self._page
        context = self._context

        self._page = None
        self._context = None

        if page is not None:
            try:
                if not page.is_closed():
                    page.close()
            except Exception:
                pass

        if context is not None:
            try:
                context.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # PortalSession implementation
    # ------------------------------------------------------------------

    def navigate(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> None:
        """
        Navigate the active portal page.

        Navigation is delegated to BrowserEngine so browser-level
        timeout/error handling remains centralized.
        """

        self.engine.navigate(
            self.page,
            url,
            wait_until=wait_until,
        )

    def current_url(self) -> str:
        """
        Return the current page URL.
        """

        return self.page.url

    # ------------------------------------------------------------------
    # Page-level extraction
    # ------------------------------------------------------------------

    def get_text(
        self,
        selector: str,
    ) -> str:
        """
        Return visible text from the first matching element.
        """

        normalized_selector = selector.strip()

        if not normalized_selector:
            raise BrowserPageError(
                "Selector cannot be empty."
            )

        try:
            return (
                self.page
                .locator(normalized_selector)
                .first
                .inner_text()
            )

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to read text using selector "
                f"'{normalized_selector}': {exc}"
            ) from exc

    def get_texts(
        self,
        selector: str,
    ) -> list[str]:
        """
        Return visible text from all matching elements.
        """

        normalized_selector = selector.strip()

        if not normalized_selector:
            raise BrowserPageError(
                "Selector cannot be empty."
            )

        try:
            return (
                self.page
                .locator(normalized_selector)
                .all_inner_texts()
            )

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to read texts using selector "
                f"'{normalized_selector}': {exc}"
            ) from exc

    def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> str | None:
        """
        Return an attribute from the first matching element.
        """

        normalized_selector = selector.strip()
        normalized_attribute = attribute.strip()

        if not normalized_selector:
            raise BrowserPageError(
                "Selector cannot be empty."
            )

        if not normalized_attribute:
            raise BrowserPageError(
                "Attribute cannot be empty."
            )

        try:
            return (
                self.page
                .locator(normalized_selector)
                .first
                .get_attribute(normalized_attribute)
            )

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to read attribute "
                f"'{normalized_attribute}' using selector "
                f"'{normalized_selector}': {exc}"
            ) from exc

    def get_attributes(
        self,
        selector: str,
        attribute: str,
    ) -> list[str | None]:
        """
        Return an attribute from all matching elements.
        """

        normalized_selector = selector.strip()
        normalized_attribute = attribute.strip()

        if not normalized_selector:
            raise BrowserPageError(
                "Selector cannot be empty."
            )

        if not normalized_attribute:
            raise BrowserPageError(
                "Attribute cannot be empty."
            )

        try:
            return (
                self.page
                .locator(normalized_selector)
                .evaluate_all(
                    """
                    (elements, attribute) =>
                        elements.map(
                            element =>
                                element.getAttribute(attribute)
                        )
                    """,
                    normalized_attribute,
                )
            )

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to read attributes "
                f"'{normalized_attribute}' using selector "
                f"'{normalized_selector}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Scoped extraction
    # ------------------------------------------------------------------

    def get_element_count(
        self,
        selector: str,
    ) -> int:
        """
        Return the number of elements matching a selector.
        """

        normalized_selector = selector.strip()

        if not normalized_selector:
            raise BrowserPageError(
                "Selector cannot be empty."
            )

        try:
            return self.page.locator(
                normalized_selector
            ).count()

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to count elements using selector "
                f"'{normalized_selector}': {exc}"
            ) from exc

    def get_scoped_text(
        self,
        parent_selector: str,
        child_selector: str,
        index: int,
    ) -> str:
        """
        Return text from a child inside one specific parent element.

        Example:

            parent_selector =
                "article[data-job-id]"

            child_selector =
                ".job-title"

            index = 1

        This guarantees that the title is taken from job card #2,
        rather than from the first title on the page.
        """

        normalized_parent = parent_selector.strip()
        normalized_child = child_selector.strip()

        if not normalized_parent:
            raise BrowserPageError(
                "Parent selector cannot be empty."
            )

        if not normalized_child:
            raise BrowserPageError(
                "Child selector cannot be empty."
            )

        if index < 0:
            raise BrowserPageError(
                "Element index cannot be negative."
            )

        try:
            parent = (
                self.page
                .locator(normalized_parent)
                .nth(index)
            )

            child = parent.locator(
                normalized_child
            ).first

            return child.inner_text()

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to read scoped text. "
                f"Parent='{normalized_parent}', "
                f"Child='{normalized_child}', "
                f"Index={index}: {exc}"
            ) from exc

    def get_scoped_attribute(
        self,
        parent_selector: str,
        child_selector: str,
        attribute: str,
        index: int,
    ) -> str | None:
        """
        Return an attribute from a child inside one specific parent.

        This is used to extract the correct URL from the corresponding
        LinkedIn job card.
        """

        normalized_parent = parent_selector.strip()
        normalized_child = child_selector.strip()
        normalized_attribute = attribute.strip()

        if not normalized_parent:
            raise BrowserPageError(
                "Parent selector cannot be empty."
            )

        if not normalized_child:
            raise BrowserPageError(
                "Child selector cannot be empty."
            )

        if not normalized_attribute:
            raise BrowserPageError(
                "Attribute cannot be empty."
            )

        if index < 0:
            raise BrowserPageError(
                "Element index cannot be negative."
            )

        try:
            parent = (
                self.page
                .locator(normalized_parent)
                .nth(index)
            )

            child = parent.locator(
                normalized_child
            ).first

            return child.get_attribute(
                normalized_attribute
            )

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to read scoped attribute. "
                f"Parent='{normalized_parent}', "
                f"Child='{normalized_child}', "
                f"Attribute='{normalized_attribute}', "
                f"Index={index}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def click(
        self,
        selector: str,
    ) -> None:
        """
        Click the first matching page element.
        """

        normalized_selector = selector.strip()

        if not normalized_selector:
            raise BrowserPageError(
                "Selector cannot be empty."
            )

        try:
            (
                self.page
                .locator(normalized_selector)
                .first
                .click()
            )

        except Exception as exc:
            raise BrowserPageError(
                f"Failed to click selector "
                f"'{normalized_selector}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Additional browser capabilities
    # ------------------------------------------------------------------

    def screenshot(
        self,
        *,
        name: str,
        full_page: bool = True,
    ) -> Path:
        """
        Capture a screenshot using BrowserEngine.
        """

        return self.engine.screenshot(
            self.page,
            name=name,
            full_page=full_page,
        )

    def start_tracing(
        self,
        *,
        screenshots: bool = True,
        snapshots: bool = True,
        sources: bool = True,
    ) -> None:
        """
        Start Playwright tracing for this portal session.
        """

        self.engine.start_tracing(
            self.context,
            screenshots=screenshots,
            snapshots=snapshots,
            sources=sources,
        )

    def stop_tracing(
        self,
        *,
        name: str,
    ) -> Path:
        """
        Stop tracing and return the generated trace path.
        """

        return self.engine.stop_tracing(
            self.context,
            name=name,
        )

    def save_storage_state(
        self,
        path: str | Path,
    ) -> Path:
        """
        Save the authenticated browser storage state.

        This will later allow supported portals to persist sessions
        without storing raw passwords in the application.
        """

        output_path = Path(path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            self.context.storage_state(
                path=str(output_path)
            )

        except Exception as exc:
            raise BrowserContextError(
                f"Failed to save browser storage state: {exc}"
            ) from exc

        return output_path
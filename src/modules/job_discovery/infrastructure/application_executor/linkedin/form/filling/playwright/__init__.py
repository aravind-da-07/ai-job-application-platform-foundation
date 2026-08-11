"""
Playwright-backed LinkedIn application form filling.
"""

from src.modules.job_discovery.infrastructure.application_executor.linkedin.form.filling.playwright.playwright_field_filler import (
    PlaywrightLinkedInApplicationFieldFiller,
)

__all__ = [
    "PlaywrightLinkedInApplicationFieldFiller",
]
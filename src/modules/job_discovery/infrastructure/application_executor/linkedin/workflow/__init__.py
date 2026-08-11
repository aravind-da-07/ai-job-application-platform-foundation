"""
LinkedIn browser execution workflow.

Coordinates form detection, approved field filling, and submission.
"""

from src.modules.job_discovery.infrastructure.application_executor.linkedin.workflow.linkedin_browser_workflow import (
    LinkedInBrowserExecutionWorkflow,
)

__all__ = [
    "LinkedInBrowserExecutionWorkflow",
]
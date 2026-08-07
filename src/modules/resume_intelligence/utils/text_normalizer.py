"""
Text Normalizer.

Provides common text cleanup for parsed resumes.
"""

from __future__ import annotations

import re


class TextNormalizer:
    """
    Normalizes extracted resume text.
    """

    @staticmethod
    def normalize(text: str) -> str:
        """
        Clean extracted resume text.
        """

        # Normalize escaped characters.
        text = text.replace("\\:", ":")

        # Replace Markdown mailto links.
        text = TextNormalizer._replace_mailto_links(text)

        # Replace generic Markdown hyperlinks.
        text = TextNormalizer._replace_markdown_links(text)

        # Normalize line endings.
        text = text.replace("\r\n", "\n")

        return text.strip()

    @staticmethod
    def _replace_mailto_links(text: str) -> str:
        """
        Converts:

        [john@example.com](mailto:john@example.com)

        to:

        john@example.com
        """

        while True:
            start = text.find("[")
            if start == -1:
                break

            end = text.find("]", start)
            if end == -1:
                break

            open_paren = text.find("(", end)
            if open_paren == -1:
                break

            close_paren = text.find(")", open_paren)
            if close_paren == -1:
                break

            markdown = text[start : close_paren + 1]

            if "mailto:" not in markdown.lower():
                text = (
                    text[: start]
                    + markdown
                    + text[close_paren + 1 :]
                )
                break

            email = text[start + 1 : end]

            text = (
                text[:start]
                + email
                + text[close_paren + 1 :]
            )

        return text

    @staticmethod
    def _replace_markdown_links(text: str) -> str:
        """
        Converts:

        [GitHub](https://github.com/user)

        to:

        https://github.com/user
        """

        return re.sub(
            r"\[([^\]]+)\]\((https?://[^)]+)\)",
            r"\2",
            text,
            flags=re.IGNORECASE,
        )


__all__ = ["TextNormalizer"]
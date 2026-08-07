"""
Text Processor.

Provides reusable text preprocessing utilities for Resume Intelligence.
"""

from __future__ import annotations

import re


class TextProcessor:
    """
    Provides reusable text preprocessing utilities.
    """

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize whitespace and line endings.
        """

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        text = re.sub(
            r"\n{2,}",
            "\n",
            text,
        )

        return text.strip()

    @staticmethod
    def lowercase(text: str) -> str:
        """
        Returns lowercase text.
        """

        return text.lower()

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """
        Tokenizes text into lowercase words.
        """

        return re.findall(
            r"[A-Za-z0-9+#.&-]+",
            text.lower(),
        )

    @staticmethod
    def unique_tokens(text: str) -> set[str]:
        """
        Returns unique normalized tokens.
        """

        return set(
            TextProcessor.tokenize(text)
        )

    @staticmethod
    def contains_phrase(
        text: str,
        phrase: str,
    ) -> bool:
        """
        Returns True if phrase exists.
        """

        return phrase.lower() in text.lower()


__all__ = [
    "TextProcessor",
]
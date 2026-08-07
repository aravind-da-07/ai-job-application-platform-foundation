"""
Base Extractor.

Defines the common interface for all resume extractors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class BaseExtractor(ABC, Generic[InputType, OutputType]):
    """
    Abstract base class for all extractors.
    """

    @abstractmethod
    def extract(self, data: InputType) -> OutputType:
        """
        Extract structured information from the supplied data.
        """
        raise NotImplementedError
"""
Storage abstraction.

The application layer depends on this interface rather than directly
depending on Supabase Storage or the local filesystem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageAdapter(ABC):
    """
    Abstract interface for application file storage.
    """

    @abstractmethod
    def upload(
        self,
        source_path: str | Path,
        destination_path: str,
    ) -> str:
        """
        Upload a local file and return its logical storage path.
        """
        raise NotImplementedError

    @abstractmethod
    def download(
        self,
        storage_path: str,
        destination_path: str | Path,
    ) -> Path:
        """
        Download a stored file to a local destination.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        storage_path: str,
    ) -> None:
        """
        Delete a stored file.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        storage_path: str,
    ) -> bool:
        """
        Return whether a stored object exists.
        """
        raise NotImplementedError
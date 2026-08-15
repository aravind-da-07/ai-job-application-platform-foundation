"""
Local filesystem storage adapter.

Used for local development and testing.

The application does not depend on this implementation directly;
it depends on StorageAdapter.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from src.shared.core.exceptions import StorageError
from src.shared.storage.storage_adapter import StorageAdapter


class LocalStorageAdapter(StorageAdapter):
    """
    Stores application files on the local filesystem.
    """

    def __init__(
        self,
        root_directory: str | Path,
    ) -> None:
        self._root = Path(root_directory)

        try:
            self._root.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as exc:
            raise StorageError(
                "Unable to initialize local storage.",
                details={
                    "root_directory": str(self._root),
                    "cause": str(exc),
                },
            ) from exc

    def upload(
        self,
        source_path: str | Path,
        destination_path: str,
    ) -> str:
        source = Path(source_path)

        if not source.exists():
            raise StorageError(
                f"Source file does not exist: {source}"
            )

        if not source.is_file():
            raise StorageError(
                f"Source path is not a file: {source}"
            )

        destination = self._resolve_destination(
            destination_path
        )

        try:
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source,
                destination,
            )
        except OSError as exc:
            raise StorageError(
                "Unable to upload file to local storage.",
                details={
                    "source": str(source),
                    "destination": str(destination),
                    "cause": str(exc),
                },
            ) from exc

        return destination_path.replace("\\", "/")

    def download(
        self,
        storage_path: str,
        destination_path: str | Path,
    ) -> Path:
        source = self._resolve_destination(storage_path)

        if not source.exists():
            raise StorageError(
                f"Stored file does not exist: {storage_path}"
            )

        destination = Path(destination_path)

        try:
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source,
                destination,
            )
        except OSError as exc:
            raise StorageError(
                "Unable to download file from local storage.",
                details={
                    "storage_path": storage_path,
                    "destination": str(destination),
                    "cause": str(exc),
                },
            ) from exc

        return destination

    def delete(
        self,
        storage_path: str,
    ) -> None:
        path = self._resolve_destination(storage_path)

        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            raise StorageError(
                "Unable to delete stored file.",
                details={
                    "storage_path": storage_path,
                    "cause": str(exc),
                },
            ) from exc

    def exists(
        self,
        storage_path: str,
    ) -> bool:
        return self._resolve_destination(
            storage_path
        ).is_file()

    def _resolve_destination(
        self,
        storage_path: str,
    ) -> Path:
        """
        Resolve a logical storage path safely under the root directory.
        """

        relative = Path(storage_path)

        if relative.is_absolute():
            raise StorageError(
                "Storage path must be relative."
            )

        resolved = (
            self._root / relative
        ).resolve()

        root = self._root.resolve()

        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise StorageError(
                "Storage path escapes the configured storage root."
            ) from exc

        return resolved
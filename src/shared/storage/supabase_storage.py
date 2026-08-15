"""
Supabase Storage adapter.

This module is the infrastructure boundary between the application
and Supabase Storage.

The service-role key is used only inside this infrastructure layer.
It must never be exposed through API responses or frontend code.
"""

from __future__ import annotations

from pathlib import Path

from supabase import Client, create_client

from src.shared.config.settings import get_settings
from src.shared.core.exceptions import StorageError
from src.shared.storage.storage_adapter import StorageAdapter


class SupabaseStorageAdapter(StorageAdapter):
    """
    Stores application files in Supabase Storage.
    """

    def __init__(
        self,
        *,
        client: Client | None = None,
        bucket_name: str | None = None,
    ) -> None:
        settings = get_settings()

        self._bucket_name = (
            bucket_name
            or settings.supabase_storage_bucket
        )

        if not self._bucket_name:
            raise StorageError(
                "Supabase Storage bucket is not configured."
            )

        if client is not None:
            self._client = client
        else:
            if not settings.supabase_url:
                raise StorageError(
                    "Supabase URL is not configured."
                )

            if not settings.supabase_service_role_key:
                raise StorageError(
                    "Supabase service-role key is not configured."
                )

            try:
                self._client = create_client(
                    settings.supabase_url,
                    settings.supabase_service_role_key,
                )
            except Exception as exc:
                raise StorageError(
                    "Unable to initialize Supabase Storage client.",
                    details={
                        "cause": str(exc),
                    },
                ) from exc

    def upload(
        self,
        source_path: str | Path,
        destination_path: str,
    ) -> str:
        """
        Upload a local file to Supabase Storage.

        Returns:
            Logical storage path inside the configured bucket.
        """

        source = Path(source_path)

        if not source.exists():
            raise StorageError(
                f"Source file does not exist: {source}"
            )

        if not source.is_file():
            raise StorageError(
                f"Source path is not a file: {source}"
            )

        try:
            file_bytes = source.read_bytes()

            self._client.storage.from_(
                self._bucket_name
            ).upload(
                destination_path,
                file_bytes,
                {
                    "content-type": self._content_type(source),
                    "upsert": False,
                },
            )

        except Exception as exc:
            raise StorageError(
                "Unable to upload file to Supabase Storage.",
                details={
                    "bucket": self._bucket_name,
                    "storage_path": destination_path,
                    "cause": str(exc),
                },
            ) from exc

        return destination_path.replace("\\", "/")

    def download(
        self,
        storage_path: str,
        destination_path: str | Path,
    ) -> Path:
        """
        Download a file from Supabase Storage.
        """

        destination = Path(destination_path)

        try:
            file_bytes = (
                self._client.storage
                .from_(self._bucket_name)
                .download(storage_path)
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination.write_bytes(file_bytes)

        except Exception as exc:
            raise StorageError(
                "Unable to download file from Supabase Storage.",
                details={
                    "bucket": self._bucket_name,
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
        """
        Delete a file from Supabase Storage.
        """

        try:
            (
                self._client.storage
                .from_(self._bucket_name)
                .remove([storage_path])
            )

        except Exception as exc:
            raise StorageError(
                "Unable to delete file from Supabase Storage.",
                details={
                    "bucket": self._bucket_name,
                    "storage_path": storage_path,
                    "cause": str(exc),
                },
            ) from exc

    def exists(
        self,
        storage_path: str,
    ) -> bool:
        """
        Determine whether an object exists.

        Supabase Storage does not expose a simple universal `exists`
        operation, so this implementation checks the parent directory.
        """

        path = Path(storage_path)

        parent = str(path.parent).replace("\\", "/")

        if parent == ".":
            parent = ""

        filename = path.name

        try:
            files = (
                self._client.storage
                .from_(self._bucket_name)
                .list(parent)
            )

            return any(
                item.get("name") == filename
                for item in files
            )

        except Exception as exc:
            raise StorageError(
                "Unable to check Supabase Storage object.",
                details={
                    "bucket": self._bucket_name,
                    "storage_path": storage_path,
                    "cause": str(exc),
                },
            ) from exc

    @staticmethod
    def _content_type(
        file_path: Path,
    ) -> str:
        """
        Determine a reasonable MIME type for the uploaded file.
        """

        extension = file_path.suffix.lower()

        content_types = {
            ".pdf": "application/pdf",
            ".docx": (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            ".txt": "text/plain",
        }

        return content_types.get(
            extension,
            "application/octet-stream",
        )


__all__ = ["SupabaseStorageAdapter"]
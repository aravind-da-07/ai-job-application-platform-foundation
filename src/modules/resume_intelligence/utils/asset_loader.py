"""
Asset Loader.

Provides reusable utilities for loading text-based assets bundled with
the Resume Intelligence module.
"""

from __future__ import annotations

from pathlib import Path


class AssetLoader:
    """
    Loads text assets from the Resume Intelligence assets directory.
    """

    def __init__(self) -> None:
        self._assets_root = (
            Path(__file__).resolve().parent.parent / "assets"
        )

    def read_text(self, relative_path: str) -> str:
        """
        Reads a UTF-8 encoded text asset.

        Parameters
        ----------
        relative_path:
            Relative path inside the assets directory.

        Returns
        -------
        str
            Contents of the text file.
        """

        file_path = self._assets_root / relative_path

        if not file_path.exists():
            raise FileNotFoundError(
                f"Asset not found: {file_path}"
            )

        return file_path.read_text(
            encoding="utf-8"
        )

    def read_lines(self, relative_path: str) -> list[str]:
        """
        Reads non-empty lines from a text asset.

        Blank lines are ignored.
        """

        return [
            line.strip()
            for line in self.read_text(relative_path).splitlines()
            if line.strip()
        ]


__all__ = ["AssetLoader"]
from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    """Abstract interface for vault storage backends."""

    def __init__(self) -> None:
        self._write_generation: int = 0

    @property
    def write_generation(self) -> int:
        """Monotonic counter incremented on every write/delete."""
        return self._write_generation

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read file content. Path is relative to vault root."""
        ...

    @abstractmethod
    def write_file(self, path: str, content: str) -> dict:
        """Write content to file. Creates parent dirs if needed.

        Returns dict with 'path' and 'status' keys.
        """
        ...

    @abstractmethod
    def list_files(self, directory: str = "", extension: str = ".md") -> list[str]:
        """List files recursively under directory filtered by extension.

        Returns relative paths as strings.
        """
        ...

    @abstractmethod
    def delete_file(self, path: str) -> dict:
        """Delete a file. Path is relative to vault root.

        Returns dict with 'path' and 'status' keys.
        """
        ...

    @abstractmethod
    def search_files(self, query: str, directory: str = "") -> list[dict]:
        """Search for query in filenames and content (case-insensitive).

        Returns list of dicts with 'path', 'filename', and 'snippet' keys.
        """
        ...

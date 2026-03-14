from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    """Abstract interface for vault storage backends."""

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
    def list_files(self, directory: str = "") -> list[str]:
        """List all .md files recursively under directory.

        Returns relative paths as strings.
        """
        ...

    @abstractmethod
    def search_files(self, query: str, directory: str = "") -> list[dict]:
        """Search for query in filenames and content (case-insensitive).

        Returns list of dicts with 'path', 'filename', and 'snippet' keys.
        """
        ...

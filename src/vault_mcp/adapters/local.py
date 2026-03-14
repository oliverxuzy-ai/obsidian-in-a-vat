import logging
from pathlib import Path

from vault_mcp.adapters.base import StorageAdapter

logger = logging.getLogger("vault-mcp.adapters.local")


class LocalStorageAdapter(StorageAdapter):
    """Storage adapter for the local filesystem."""

    def __init__(self, vault_path: str) -> None:
        self.vault_path = Path(vault_path).resolve()
        self.vault_path.mkdir(parents=True, exist_ok=True)
        logger.info("Vault root: %s", self.vault_path)

    def _resolve_safe(self, relative_path: str) -> Path:
        """Resolve a relative path and verify it stays within the vault."""
        full = (self.vault_path / relative_path).resolve()
        if not full.is_relative_to(self.vault_path):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return full

    def read_file(self, path: str) -> str:
        try:
            full = self._resolve_safe(path)
            return full.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Error reading {path}: {e}") from e

    def write_file(self, path: str, content: str) -> dict:
        try:
            full = self._resolve_safe(path)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            logger.info("Wrote file: %s", path)
            return {"path": path, "status": "written"}
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Error writing {path}: {e}") from e

    def list_files(self, directory: str = "") -> list[str]:
        try:
            base = self._resolve_safe(directory) if directory else self.vault_path
            return sorted(
                str(p.relative_to(self.vault_path))
                for p in base.rglob("*.md")
                if not any(part.startswith(".") for part in p.relative_to(self.vault_path).parts)
            )
        except Exception as e:
            logger.error("Error listing files in %s: %s", directory, e)
            return []

    def search_files(self, query: str, directory: str = "") -> list[dict]:
        results: list[dict] = []
        query_lower = query.lower()

        try:
            files = self.list_files(directory)
        except Exception as e:
            logger.error("Error searching files: %s", e)
            return []

        for rel_path in files:
            try:
                full = self._resolve_safe(rel_path)
                filename = full.name
                content = full.read_text(encoding="utf-8")

                if query_lower in filename.lower() or query_lower in content.lower():
                    results.append({
                        "path": rel_path,
                        "filename": filename,
                        "snippet": content[:200],
                    })
            except Exception as e:
                logger.warning("Skipping %s during search: %s", rel_path, e)
                continue

        return results

import logging

import frontmatter

from vault_mcp.adapters.base import StorageAdapter

logger = logging.getLogger("vault-mcp.tools.read")


def register_read_tools(mcp, adapter: StorageAdapter) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    def vault_search(
        query: str,
        directory: str = "",
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Search the vault for notes matching a query.

        Args:
            query: Text to search for in filenames and content
            directory: Subdirectory to search within (default: entire vault)
            tags: Optional tags to filter results by
        """
        filter_tags = tags or []
        results = adapter.search_files(query, directory)

        # Filter by frontmatter tags if requested
        if filter_tags:
            filtered = []
            for r in results:
                try:
                    content = adapter.read_file(r["path"])
                    post = frontmatter.loads(content)
                    file_tags = post.metadata.get("tags", [])
                    if any(t in file_tags for t in filter_tags):
                        filtered.append(r)
                except Exception:
                    continue
            results = filtered

        # Build output with frontmatter metadata
        output = []
        for r in results:
            entry: dict = {"path": r["path"]}
            try:
                content = adapter.read_file(r["path"])
                post = frontmatter.loads(content)
                entry["title"] = post.metadata.get("title", r.get("filename", ""))
                entry["status"] = post.metadata.get("status", "")
                entry["tags"] = post.metadata.get("tags", [])
                entry["created"] = post.metadata.get("created", "")
                entry["preview"] = post.content[:200]
            except Exception:
                entry["title"] = r.get("filename", "")
                entry["preview"] = r.get("snippet", "")
            output.append(entry)

        return output

    @mcp.tool(annotations={"readOnlyHint": True})
    def vault_read(path: str) -> str:
        """Read the full content of a vault note.

        Args:
            path: Relative path to the file within the vault
        """
        return adapter.read_file(path)

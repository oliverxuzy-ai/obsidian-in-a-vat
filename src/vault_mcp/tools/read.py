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

    @mcp.tool(annotations={"readOnlyHint": True})
    def vault_list_captures(
        status: str = "capture",
        limit: int = 50,
    ) -> list[dict]:
        """List captures filtered by status, sorted newest first.

        Args:
            status: Filter by status — "capture" (unpromoted, default),
                    "promoted" (already promoted), or "all" (everything)
            limit: Maximum number of results to return (default 50)
        """
        try:
            files = adapter.list_files("captures")
        except Exception as e:
            logger.warning("Error listing captures: %s", e)
            return []

        captures: list[dict] = []
        for path in files:
            try:
                content = adapter.read_file(path)
                post = frontmatter.loads(content)
                file_status = post.metadata.get("status", "capture")

                if status != "all" and file_status != status:
                    continue

                captures.append({
                    "path": path,
                    "title": post.metadata.get("title", ""),
                    "status": file_status,
                    "created": post.metadata.get("created", ""),
                    "tags": post.metadata.get("tags", []),
                    "preview": post.content[:200],
                })
            except Exception:
                continue

        # Sort by filename descending (filenames are timestamped)
        captures.sort(key=lambda c: c["path"], reverse=True)
        return captures[:limit]

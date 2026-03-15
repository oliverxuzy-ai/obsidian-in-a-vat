import logging

import frontmatter

from vault_mcp.adapters.base import StorageAdapter

logger = logging.getLogger("vault-mcp.tools.read")


def _handle_search(adapter: StorageAdapter, query, directory, tags) -> list[dict]:
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


def _handle_get(adapter: StorageAdapter, path) -> str:
    return adapter.read_file(path)


def _handle_list_captures(adapter: StorageAdapter, status, limit, include_content) -> list[dict]:
    try:
        files = adapter.list_files("captures")
    except Exception as e:
        logger.warning("Error listing captures: %s", e)
        return []

    captures: list[dict] = []
    for file_path in files:
        try:
            content = adapter.read_file(file_path)
            post = frontmatter.loads(content)
            file_status = post.metadata.get("status", "capture")

            if status != "all" and file_status != status:
                continue

            entry: dict = {
                "path": file_path,
                "title": post.metadata.get("title", ""),
                "status": file_status,
                "created": post.metadata.get("created", ""),
                "tags": post.metadata.get("tags", []),
            }
            if include_content:
                entry["content"] = content
            else:
                entry["preview"] = post.content[:200]
            captures.append(entry)
        except Exception:
            continue

    # Sort by filename descending (filenames are timestamped)
    captures.sort(key=lambda c: c["path"], reverse=True)
    return captures[:limit]


def register_read_tools(mcp, adapter: StorageAdapter) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    def vault_read(
        action: str,
        query: str = "",
        directory: str = "",
        tags: list[str] | None = None,
        path: str = "",
        status: str = "capture",
        limit: int = 50,
        include_content: bool = False,
    ) -> list[dict] | str:
        """Read and search vault content.

        Actions:
          search: Search vault notes.
            params: query, directory, tags
          get: Read a single file's full content.
            params: path
          list_captures: List captures filtered by status, sorted newest first.
            params: status ("capture" | "promoted" | "all"),
                    limit (default 50),
                    include_content (default False)
        """
        if action == "search":
            return _handle_search(adapter, query, directory, tags)
        elif action == "get":
            return _handle_get(adapter, path)
        elif action == "list_captures":
            return _handle_list_captures(adapter, status, limit, include_content)
        else:
            return {"status": "error", "message": f"Unknown action '{action}'. Valid: search, get, list_captures"}

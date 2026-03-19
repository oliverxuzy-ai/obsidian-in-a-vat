"""Shared test fixtures: in-memory StorageAdapter and MCP stub."""

from __future__ import annotations

import pytest
import frontmatter

from vault_mcp.adapters.base import StorageAdapter


class MemoryAdapter(StorageAdapter):
    """In-memory storage adapter for testing."""

    def __init__(self, files: dict[str, str] | None = None):
        self.files: dict[str, str] = dict(files or {})

    def read_file(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]

    def write_file(self, path: str, content: str) -> dict:
        self.files[path] = content
        return {"path": path, "status": "written"}

    def delete_file(self, path: str) -> dict:
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        del self.files[path]
        return {"path": path, "status": "deleted"}

    def list_files(self, directory: str = "") -> list[str]:
        return sorted(
            p for p in self.files if p.endswith(".md") and p.startswith(directory)
        )

    def search_files(self, query: str, directory: str = "") -> list[dict]:
        results = []
        q = query.lower()
        for path, content in self.files.items():
            if directory and not path.startswith(directory):
                continue
            if q in path.lower() or q in content.lower():
                results.append({"path": path, "filename": path.split("/")[-1], "snippet": content[:200]})
        return results


class McpStub:
    """Minimal stub that collects @mcp.tool() registrations."""

    def __init__(self):
        self.tools: dict[str, callable] = {}

    def tool(self, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def make_capture(title: str, insight: str, tags: list[str] | None = None, status: str = "capture") -> str:
    """Build a capture markdown string with frontmatter."""
    metadata = {
        "title": title,
        "status": status,
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "source": "conversation",
        "tags": tags or [],
        "aliases": [],
    }
    post = frontmatter.Post(insight, **metadata)
    return frontmatter.dumps(post)


def make_note(
    title: str,
    summary: str,
    content: str = "",
    tags: list[str] | None = None,
    domain: str = "",
    aliases: list[str] | None = None,
    promoted_from: list[str] | None = None,
    topics: list[str] | None = None,
) -> str:
    """Build a note markdown string with frontmatter."""
    metadata = {
        "title": title,
        "status": "note",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "domain": domain,
        "confidence": 0.7,
        "tags": tags or [],
        "aliases": aliases or [],
        "promoted_from": promoted_from or [],
    }
    if topics is not None:
        metadata["topics"] = topics
    body = f"# Summary\n\n{summary}\n\n# Notes\n\n{content or summary}\n\n# Links\n\n"
    post = frontmatter.Post(body, **metadata)
    return frontmatter.dumps(post)


def make_topic(
    title: str,
    content: str,
    member_notes: list[str] | None = None,
    tags: list[str] | None = None,
    domain: str = "",
    graph_generation: int = 0,
) -> str:
    """Build a topic markdown string with frontmatter."""
    metadata = {
        "title": title,
        "status": "topic",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "domain": domain,
        "tags": tags or [],
        "aliases": [],
        "member_notes": member_notes or [],
        "graph_generation": graph_generation,
    }
    post = frontmatter.Post(content, **metadata)
    return frontmatter.dumps(post)


@pytest.fixture
def adapter():
    return MemoryAdapter()


@pytest.fixture
def mcp_stub():
    return McpStub()

import logging
import re
from datetime import datetime, timezone

import frontmatter
import yaml

from vault_mcp.adapters.base import StorageAdapter

logger = logging.getLogger("vault-mcp.tools.write")

DEFAULT_DOMAIN_TAGS = [
    "ai", "llm", "productivity", "writing", "coding",
    "design", "business", "learning", "health", "finance",
    "philosophy", "psychology",
]


def _generate_slug(thought: str) -> str:
    """Generate a URL-friendly slug from the first 5 words."""
    words = re.findall(r"[a-zA-Z0-9]+", thought.lower())[:5]
    return "-".join(words) if words else "untitled"


def _generate_title(thought: str) -> str:
    """Generate a title from the first ~8 words of the thought."""
    words = thought.split()[:8]
    title = " ".join(words)
    if len(thought.split()) > 8:
        title += "..."
    return title


def _load_tags_yaml(adapter: StorageAdapter) -> dict[str, list[str]]:
    """Load tags.yaml from vault root if it exists.

    Returns a mapping of tag -> list of synonyms/aliases.
    """
    try:
        content = adapter.read_file("tags.yaml")
        data = yaml.safe_load(content)
        if isinstance(data, dict) and "tags" in data:
            tag_map = {}
            for tag, synonyms in data["tags"].items():
                tag = str(tag).lower()
                if isinstance(synonyms, list):
                    tag_map[tag] = [str(s).lower() for s in synonyms]
                else:
                    tag_map[tag] = []
            return tag_map
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("Error loading tags.yaml: %s", e)
    return {}


def _collect_existing_tags(adapter: StorageAdapter) -> set[str]:
    """Scan existing vault files and collect all tags from frontmatter."""
    tags: set[str] = set()
    try:
        files = adapter.list_files()
        for path in files:
            try:
                content = adapter.read_file(path)
                post = frontmatter.loads(content)
                file_tags = post.metadata.get("tags", [])
                if isinstance(file_tags, list):
                    tags.update(str(t).lower() for t in file_tags)
            except Exception:
                continue
    except Exception as e:
        logger.warning("Error collecting existing tags: %s", e)
    return tags


def _extract_auto_tags(
    thought: str,
    tags_yaml: dict[str, list[str]],
    existing_tags: set[str],
) -> list[str]:
    """Extract tags from thought text using three sources:
    1. tags.yaml config (with synonym matching)
    2. Existing vault tags
    3. Default domain tag list (fallback)
    """
    text_lower = thought.lower()
    matched: set[str] = set()

    # Source 1: tags.yaml with synonyms
    for tag, synonyms in tags_yaml.items():
        terms = [tag] + synonyms
        for term in terms:
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, text_lower):
                matched.add(tag)
                break

    # Source 2: existing vault tags
    for tag in existing_tags:
        if tag not in matched:
            pattern = rf"\b{re.escape(tag)}\b"
            if re.search(pattern, text_lower):
                matched.add(tag)

    # Source 3: default domain tags (fallback for tags not yet matched)
    for tag in DEFAULT_DOMAIN_TAGS:
        if tag not in matched:
            pattern = rf"\b{re.escape(tag)}\b"
            if re.search(pattern, text_lower):
                matched.add(tag)

    return sorted(matched)


def register_write_tools(mcp, adapter: StorageAdapter) -> None:
    # Pre-load tag sources at registration time
    tags_yaml = _load_tags_yaml(adapter)
    existing_tags = _collect_existing_tags(adapter)

    @mcp.tool(
        annotations={"destructiveHint": False, "idempotentHint": False}
    )
    def vault_capture(
        thought: str,
        tags: list[str] | None = None,
    ) -> dict:
        """Capture a thought or insight into the vault.

        Args:
            thought: The content/thought to capture
            tags: Optional list of tags to categorize the capture
        """
        nonlocal existing_tags

        user_tags = tags or []
        now = datetime.now(timezone.utc)
        slug = _generate_slug(thought)
        title = _generate_title(thought)
        timestamp_str = now.strftime("%Y-%m-%d-%H%M%S")
        filename = f"captures/{timestamp_str}-{slug}.md"

        # Refresh existing tags on each capture
        existing_tags = _collect_existing_tags(adapter)

        auto_tags = _extract_auto_tags(thought, tags_yaml, existing_tags)
        all_tags = sorted(set(user_tags + auto_tags))

        # Build content following templates/capture.md format
        iso_now = now.isoformat()
        metadata = {
            "title": title,
            "status": "capture",
            "created": iso_now,
            "updated": iso_now,
            "source": "claude-chat",
            "tags": all_tags,
            "aliases": [],
        }

        body = (
            f"## Capture\n\n"
            f"{thought}\n\n"
            f"## Next\n\n"
            f"- Why does this matter?\n"
            f"- What should this connect to later?"
        )

        post = frontmatter.Post(body, **metadata)
        content = frontmatter.dumps(post)

        result = adapter.write_file(filename, content)

        # Find related captures by searching for matching tags
        related: list[str] = []
        if all_tags:
            for tag in all_tags[:3]:  # search first 3 tags
                try:
                    search_results = adapter.search_files(tag, "captures")
                    for r in search_results:
                        if r["path"] != filename and r["path"] not in related:
                            related.append(r["path"])
                except Exception:
                    continue

        return {
            "status": "success",
            "path": result["path"],
            "title": title,
            "tags": all_tags,
            "related_captures": related[:5],
        }

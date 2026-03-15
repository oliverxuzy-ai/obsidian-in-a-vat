import logging
import re
from datetime import datetime, timezone

import frontmatter
import yaml

from vault_mcp.adapters.base import StorageAdapter
from vault_mcp.utils.markdown import auto_insert_wikilinks, collect_note_titles

logger = logging.getLogger("vault-mcp.tools.write")

DEFAULT_DOMAIN_TAGS = [
    "ai", "llm", "productivity", "writing", "coding",
    "design", "business", "learning", "health", "finance",
    "philosophy", "psychology",
]


def _generate_slug(*candidates: str) -> str:
    """Generate a URL-friendly slug from the first candidate with ASCII words."""
    for candidate in candidates:
        words = re.findall(r"[a-zA-Z0-9]+", candidate.lower())[:5]
        if words:
            return "-".join(words)
    return "capture"


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
    # Pre-load tag sources and note titles at registration time
    tags_yaml = _load_tags_yaml(adapter)
    existing_tags = _collect_existing_tags(adapter)
    title_cache = collect_note_titles(adapter)

    VALID_SOURCE_TYPES = {"conversation", "article", "flash"}

    @mcp.tool(
        annotations={"destructiveHint": False, "idempotentHint": False}
    )
    def vault_capture(
        title: str,
        insight: str,
        source_type: str = "conversation",
        original: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Capture a refined insight into the vault.

        WORKFLOW — Claude MUST follow these steps before calling this tool:
        1. REFINE: Distill the user's thought into a core insight (1–3 plain-text
           sentences). Generate a clean, descriptive plain-text title (≤50 chars).
        2. CONFIRM: Present the refinement to the user and wait for approval.
           Refinement is lossy — only the user knows which version captures
           what they truly want to remember. Do NOT call this tool until the
           user explicitly confirms.
        3. STORE: Call this tool with the confirmed title, insight, and metadata.

        Args:
            title: Plain-text title (≤50 characters). Used for filename and
                frontmatter. Example: "Spaced repetition and desirable difficulty"
            insight: Core insight in 1–3 sentences, plain text. The refined,
                confirmed version of what the user wants to remember.
            source_type: Origin of the thought — "conversation", "article", or
                "flash". Defaults to "conversation".
            original: Optional verbatim original material for reference. Include
                when the user wants to preserve the source text alongside the
                refined insight.
            tags: Optional list of tags. If omitted, tags are auto-extracted
                from the insight text.
        """
        # Validate source_type
        if source_type not in VALID_SOURCE_TYPES:
            return {
                "status": "error",
                "message": f"Invalid source_type '{source_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_SOURCE_TYPES))}",
            }

        # Truncate title if over 50 characters
        if len(title) > 50:
            logger.warning("Title truncated from %d to 50 characters", len(title))
            title = title[:50]

        user_tags = tags or []
        now = datetime.now(timezone.utc)
        slug = _generate_slug(title, insight)
        timestamp_str = now.strftime("%Y-%m-%d-%H%M%S")
        filename = f"captures/{timestamp_str}-{slug}.md"

        auto_tags = _extract_auto_tags(insight, tags_yaml, existing_tags)
        all_tags = sorted(set(user_tags + auto_tags))

        # Build content: insight + optional parts separated by ---
        iso_now = now.isoformat()
        metadata = {
            "title": title,
            "status": "capture",
            "created": iso_now,
            "updated": iso_now,
            "source": source_type,
            "tags": all_tags,
            "aliases": [],
        }

        body = insight

        optional_parts = []
        if source_type != "conversation":
            optional_parts.append(f"Source: {source_type}")
        if original:
            optional_parts.append(f"Original:\n{original}")

        if optional_parts:
            body += "\n\n---\n\n" + "\n\n".join(optional_parts)

        post = frontmatter.Post(body, **metadata)
        content = frontmatter.dumps(post)

        result = adapter.write_file(filename, content)

        # Incrementally update cached tags
        existing_tags.update(t.lower() for t in all_tags)

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

    @mcp.tool(
        annotations={"destructiveHint": False, "idempotentHint": False}
    )
    def vault_promote(
        capture_paths: list[str],
        title: str,
        summary: str,
        domain: str,
        content: str,
        tags: list[str] | None = None,
        aliases: list[str] | None = None,
        confidence: float = 0.7,
        auto_link: bool = True,
    ) -> dict:
        """Promote one or more captures into a structured note.

        WORKFLOW — Claude MUST follow these steps:
        1. LIST: Call vault_list_captures(include_content=True) to get all
           unpromoted captures with full content in a single call.
        2. SELECT & SYNTHESIZE: Choose related captures to promote together.
           Generate:
           - title (descriptive, ≤60 chars)
           - summary (one sentence)
           - domain (knowledge area)
           - content (synthesized markdown combining the captures' insights)
           - confidence (0.0–1.0, your honest assessment)
           - tags (or note that capture tags will be inherited)
        3. CONFIRM: Present the full synthesis to the user and wait for
           approval. Show: title, summary, domain, content, confidence, tags,
           and which captures will be promoted. Promotion is semi-destructive
           — source captures are marked as promoted and cannot be re-promoted.
           The user may adjust any field, especially confidence. Do NOT call
           this tool until the user explicitly confirms.
        4. PROMOTE: Call this tool with the confirmed output. Do NOT call
           vault_read on individual captures — step 1 already provided full
           content.

        The tool handles file creation, frontmatter, auto-wikilink insertion,
        and marking source captures as promoted.

        Args:
            capture_paths: List of capture file paths to promote
            title: Human-readable title for the new note
            summary: One-sentence summary of the core idea
            domain: Knowledge domain (e.g. "ai", "productivity", "psychology")
            content: Synthesized note body in markdown (the Notes section)
            tags: Tags for the note (if None, inherits union of capture tags)
            aliases: Alternative names for the note
            confidence: Confidence level 0.0-1.0 (default 0.7)
            auto_link: Whether to auto-insert wikilinks to existing notes
        """
        logger.info(
            "vault_promote start: title=%r captures=%d auto_link=%s",
            title,
            len(capture_paths),
            auto_link,
        )
        try:
            # 1. Validate capture paths exist and are not already promoted
            capture_posts: list[tuple[str, frontmatter.Post]] = []
            for path in capture_paths:
                try:
                    raw = adapter.read_file(path)
                except FileNotFoundError:
                    return {"status": "error", "message": f"Capture not found: {path}"}
                post = frontmatter.loads(raw)
                if post.metadata.get("status") == "promoted":
                    return {
                        "status": "error",
                        "message": f"Already promoted: {path}",
                    }
                capture_posts.append((path, post))

            # 2. Collect tags from captures if none provided
            if tags is None:
                merged_tags: set[str] = set()
                for _, post in capture_posts:
                    file_tags = post.metadata.get("tags", [])
                    if isinstance(file_tags, list):
                        merged_tags.update(str(t).lower() for t in file_tags)
                tags = sorted(merged_tags)

            # 3. Generate slug and handle filename collision
            slug = _generate_slug(title)
            filename = f"notes/{slug}.md"
            counter = 2
            while True:
                try:
                    adapter.read_file(filename)
                    # File exists, try next suffix
                    filename = f"notes/{slug}-{counter}.md"
                    counter += 1
                except FileNotFoundError:
                    break

            # 4. Build note body
            body = (
                f"# Summary\n\n"
                f"{summary}\n\n"
                f"# Notes\n\n"
                f"{content}\n\n"
                f"# Links\n\n"
            )

            # 5. Auto-insert wikilinks to existing notes
            wikilinks_inserted: list[str] = []
            if auto_link:
                body, wikilinks_inserted = auto_insert_wikilinks(
                    body, title_cache, exclude_titles=[title.lower()]
                )

            # 6. Write the note file
            now = datetime.now(timezone.utc)
            iso_now = now.isoformat()
            metadata = {
                "title": title,
                "status": "note",
                "created": iso_now,
                "updated": iso_now,
                "domain": domain,
                "confidence": confidence,
                "tags": tags,
                "aliases": aliases or [],
                "promoted_from": capture_paths,
            }
            note_post = frontmatter.Post(body, **metadata)
            adapter.write_file(filename, frontmatter.dumps(note_post))

            # Incrementally update title cache for future wikilink insertion
            title_cache[title.lower()] = title
            for alias in (aliases or []):
                alias_str = str(alias)
                if alias_str:
                    title_cache[alias_str.lower()] = title

            # 7. Mark source captures as promoted
            for path, post in capture_posts:
                post.metadata["status"] = "promoted"
                post.metadata["promoted_to"] = filename
                post.metadata["updated"] = iso_now
                adapter.write_file(path, frontmatter.dumps(post))

            result = {
                "status": "success",
                "path": filename,
                "title": title,
                "domain": domain,
                "tags": tags,
                "promoted_from": capture_paths,
                "wikilinks_inserted": wikilinks_inserted,
            }
            logger.info("vault_promote success: path=%s", filename)
            return result
        except Exception:
            logger.exception("vault_promote failed")
            return {
                "status": "error",
                "message": "vault_promote failed unexpectedly. Check server stderr logs.",
            }

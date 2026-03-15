"""Markdown parsing utilities for vault operations.

Provides wikilink extraction, inline tag extraction,
and auto-wikilink insertion for note content.
"""

from __future__ import annotations

import re

import frontmatter

from vault_mcp.adapters.base import StorageAdapter

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]+`")


def _strip_code_blocks(text: str) -> str:
    """Remove fenced and inline code blocks from text for safe regex matching."""
    text = _FENCED_CODE_RE.sub("", text)
    text = _INLINE_CODE_RE.sub("", text)
    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_wikilinks(text: str) -> list[dict]:
    """Extract wikilinks from markdown text, excluding code blocks and embeds.

    Handles:
      - ``[[target]]``          → ``{"target": "target", "alias": None}``
      - ``[[target|alias]]``    → ``{"target": "target", "alias": "alias"}``
      - Skips ``![[embed]]``    (transclusion syntax)
      - Skips links inside fenced code blocks and inline code

    Returns a list of dicts with keys ``target`` and ``alias``.
    """
    cleaned = _strip_code_blocks(text)
    # Negative lookbehind for ! to exclude embeds
    raw_links = re.findall(r"(?<!!)\[\[([^\]]+)\]\]", cleaned)

    results: list[dict] = []
    seen: set[str] = set()
    for raw in raw_links:
        if "|" in raw:
            target, alias = raw.split("|", 1)
            target = target.strip()
            alias = alias.strip()
        else:
            target = raw.strip()
            alias = None

        if target and target not in seen:
            seen.add(target)
            results.append({"target": target, "alias": alias})

    return results


def extract_inline_tags(text: str) -> list[str]:
    """Extract inline ``#tag`` occurrences from markdown body text.

    Rules:
      - Tags must start with a letter, may contain letters, digits, ``_``, ``-``
      - Requires whitespace or start-of-line before ``#`` to avoid matching headings
      - Excludes tags inside fenced code blocks and inline code

    Returns a sorted, deduplicated list of tag strings (without the ``#`` prefix).
    """
    cleaned = _strip_code_blocks(text)
    tags = re.findall(r"(?:^|(?<=\s))#([a-zA-Z][a-zA-Z0-9_-]*)", cleaned, re.MULTILINE)
    return sorted(set(t.lower() for t in tags))


def collect_note_titles(adapter: StorageAdapter) -> dict[str, str]:
    """Scan ``notes/`` and return a mapping of lowercase title/alias → original title.

    Used for auto-wikilink insertion: if a note titled "Spaced Repetition" exists
    and the promoted content mentions "spaced repetition", we can insert
    ``[[Spaced Repetition]]``.
    """
    title_map: dict[str, str] = {}
    try:
        files = adapter.list_files("notes")
    except Exception:
        return title_map

    for path in files:
        try:
            content = adapter.read_file(path)
            post = frontmatter.loads(content)
            title = post.metadata.get("title", "")
            if title:
                title_map[title.lower()] = title
            aliases = post.metadata.get("aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    alias_str = str(alias)
                    if alias_str:
                        title_map[alias_str.lower()] = title or alias_str
        except Exception:
            continue

    return title_map


def auto_insert_wikilinks(
    content: str,
    title_map: dict[str, str],
    exclude_titles: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Replace plain-text mentions of known note titles with ``[[wikilinks]]``.

    Args:
        content: The markdown body text.
        title_map: Mapping from lowercase title/alias → original-case title.
        exclude_titles: Lowercase titles to skip (e.g. the note's own title).

    Returns:
        A tuple of (modified content, list of inserted wikilink titles).

    Rules:
      - Only replaces the **first** occurrence of each title.
      - Case-insensitive matching, but uses the original-case title in the link.
      - Skips text already inside ``[[…]]``, fenced code blocks, and inline code.
      - Matches longer phrases first to avoid partial replacements.
    """
    if not title_map:
        return content, []

    exclude = set(exclude_titles or [])
    inserted: list[str] = []

    # Sort by length descending so longer phrases match first
    sorted_keys = sorted(title_map.keys(), key=len, reverse=True)

    for key in sorted_keys:
        if key in exclude:
            continue

        original_title = title_map[key]
        # Word-boundary match, case insensitive
        # Negative lookbehind/lookahead to skip text already inside [[ ]]
        pattern = re.compile(
            r"(?<!\[\[)" + r"\b" + re.escape(key) + r"\b" + r"(?!\]\])",
            re.IGNORECASE,
        )

        # Only operate on non-code, non-wikilink zones
        # Simple approach: check if there's a match, do one replacement
        match = pattern.search(content)
        if match:
            # Verify the match is not inside a code block or existing wikilink
            start = match.start()
            prefix = content[:start]
            # Check we're not inside a fenced code block
            open_fences = prefix.count("```")
            if open_fences % 2 != 0:
                continue
            # Check we're not inside inline code
            open_backticks = prefix.count("`") - prefix.count("```") * 3
            if open_backticks % 2 != 0:
                continue

            replacement = f"[[{original_title}]]"
            content = content[:start] + replacement + content[match.end():]
            inserted.append(original_title)

    return content, inserted

"""Tests for the vault_promote tool."""

from __future__ import annotations

import frontmatter
import pytest

from vault_mcp.tools.write import register_write_tools
from tests.conftest import MemoryAdapter, McpStub, make_capture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_promote(files: dict[str, str] | None = None):
    """Register write tools against a MemoryAdapter and return (adapter, vault_promote)."""
    adapter = MemoryAdapter(files)
    mcp = McpStub()
    register_write_tools(mcp, adapter)
    return adapter, mcp.tools["vault_promote"]


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestPromoteHappyPath:
    def test_basic_promote(self):
        """Single capture promoted into a note with correct structure."""
        cap = make_capture("Test Insight", "Some insight about testing.", tags=["testing"])
        adapter, promote = setup_promote({"captures/2026-01-01-000000-test-insight.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/2026-01-01-000000-test-insight.md"],
            title="Testing Best Practices",
            summary="A summary of testing.",
            domain="engineering",
            content="Detailed notes about testing.",
        )

        assert result["status"] == "success"
        assert result["path"].startswith("notes/")
        assert result["path"].endswith(".md")
        assert result["title"] == "Testing Best Practices"
        assert result["domain"] == "engineering"
        assert result["promoted_from"] == ["captures/2026-01-01-000000-test-insight.md"]

    def test_note_file_written(self):
        """The note file actually exists in the adapter after promote."""
        cap = make_capture("Insight", "Body text.", tags=["ai"])
        adapter, promote = setup_promote({"captures/cap1.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/cap1.md"],
            title="My Note",
            summary="Summary.",
            domain="ai",
            content="Content.",
        )

        note_content = adapter.read_file(result["path"])
        post = frontmatter.loads(note_content)
        assert post.metadata["title"] == "My Note"
        assert post.metadata["status"] == "note"
        assert post.metadata["domain"] == "ai"
        assert "# Summary" in post.content
        assert "# Notes" in post.content
        assert "Content." in post.content

    def test_captures_marked_promoted(self):
        """Source captures are updated with status=promoted and promoted_to."""
        cap1 = make_capture("Cap1", "First.", tags=["a"])
        cap2 = make_capture("Cap2", "Second.", tags=["b"])
        adapter, promote = setup_promote({
            "captures/cap1.md": cap1,
            "captures/cap2.md": cap2,
        })

        result = promote(
            action="promote",
            capture_paths=["captures/cap1.md", "captures/cap2.md"],
            title="Combined",
            summary="Both.",
            domain="misc",
            content="Merged.",
        )

        for cap_path in ["captures/cap1.md", "captures/cap2.md"]:
            post = frontmatter.loads(adapter.read_file(cap_path))
            assert post.metadata["status"] == "capture"
            assert post.metadata["promoted_to"] == [result["path"]]


# ---------------------------------------------------------------------------
# Tag handling
# ---------------------------------------------------------------------------


class TestTagHandling:
    def test_tags_inherited_from_captures(self):
        """When tags=None, tags are merged from all source captures."""
        cap1 = make_capture("C1", "One.", tags=["ai", "llm"])
        cap2 = make_capture("C2", "Two.", tags=["llm", "coding"])
        adapter, promote = setup_promote({
            "captures/c1.md": cap1,
            "captures/c2.md": cap2,
        })

        result = promote(
            action="promote",
            capture_paths=["captures/c1.md", "captures/c2.md"],
            title="Merged Tags",
            summary="S.",
            domain="d",
            content="C.",
            tags=None,
        )

        assert sorted(result["tags"]) == ["ai", "coding", "llm"]

    def test_explicit_tags_override(self):
        """Explicitly provided tags are used instead of inherited ones."""
        cap = make_capture("C", "Body.", tags=["ai", "llm"])
        adapter, promote = setup_promote({"captures/c.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="Override",
            summary="S.",
            domain="d",
            content="C.",
            tags=["custom-tag"],
        )

        assert result["tags"] == ["custom-tag"]


# ---------------------------------------------------------------------------
# Slug generation & collision handling
# ---------------------------------------------------------------------------


class TestSlugAndCollision:
    def test_slug_from_title(self):
        """Note filename is derived from the title slug."""
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({"captures/c.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="My Great Note",
            summary="S.",
            domain="d",
            content="C.",
        )

        assert result["path"] == "notes/my-great-note.md"

    def test_slug_collision_appends_counter(self):
        """When a note with the same slug exists, a counter suffix is added."""
        cap = make_capture("C", "B.", tags=[])
        existing_note = frontmatter.dumps(frontmatter.Post("existing", title="Old"))
        adapter, promote = setup_promote({
            "captures/c.md": cap,
            "notes/my-note.md": existing_note,
        })

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="My Note",
            summary="S.",
            domain="d",
            content="C.",
        )

        assert result["path"] == "notes/my-note-2.md"

    def test_multiple_collisions(self):
        """Counter increments past existing suffixed files."""
        cap = make_capture("C", "B.", tags=[])
        note = frontmatter.dumps(frontmatter.Post("x", title="X"))
        adapter, promote = setup_promote({
            "captures/c.md": cap,
            "notes/my-note.md": note,
            "notes/my-note-2.md": note,
        })

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="My Note",
            summary="S.",
            domain="d",
            content="C.",
        )

        assert result["path"] == "notes/my-note-3.md"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    def test_missing_capture(self):
        """Error returned when a capture path doesn't exist."""
        adapter, promote = setup_promote()

        result = promote(
            action="promote",
            capture_paths=["captures/nonexistent.md"],
            title="T",
            summary="S.",
            domain="d",
            content="C.",
        )

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_repromote_succeeds(self):
        """A previously promoted capture can be promoted again."""
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({"captures/c.md": cap})

        # First promote
        result1 = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="First Note",
            summary="S.",
            domain="d",
            content="C.",
        )
        assert result1["status"] == "success"

        # Second promote of the same capture
        result2 = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="Second Note",
            summary="S2.",
            domain="d2",
            content="C2.",
        )
        assert result2["status"] == "success"

        # promoted_to should contain both note paths
        post = frontmatter.loads(adapter.read_file("captures/c.md"))
        assert post.metadata["status"] == "capture"
        assert post.metadata["promoted_to"] == [result1["path"], result2["path"]]

    def test_repromote_backward_compat(self):
        """Old string-style promoted_to is migrated to list on re-promote."""
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({"captures/c.md": cap})

        # Simulate old-style string promoted_to
        post = frontmatter.loads(adapter.read_file("captures/c.md"))
        post.metadata["promoted_to"] = "notes/old-note.md"
        adapter.write_file("captures/c.md", frontmatter.dumps(post))

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="New Note",
            summary="S.",
            domain="d",
            content="C.",
        )
        assert result["status"] == "success"

        post = frontmatter.loads(adapter.read_file("captures/c.md"))
        assert post.metadata["promoted_to"] == ["notes/old-note.md", result["path"]]

    def test_second_capture_missing(self):
        """Error returned for second capture when first is valid."""
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({"captures/c1.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/c1.md", "captures/c2.md"],
            title="T",
            summary="S.",
            domain="d",
            content="C.",
        )

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


# ---------------------------------------------------------------------------
# Auto-wikilink insertion
# ---------------------------------------------------------------------------


class TestAutoLink:
    def test_wikilinks_inserted(self):
        """When auto_link=True and existing notes match, wikilinks are inserted."""
        # Pre-populate a note so title_cache picks it up
        existing = frontmatter.dumps(frontmatter.Post("body", title="Spaced Repetition"))
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({
            "notes/spaced-repetition.md": existing,
            "captures/c.md": cap,
        })

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="Learning Techniques",
            summary="About spaced repetition and more.",
            domain="learning",
            content="Spaced repetition is an effective study method.",
        )

        assert "Spaced Repetition" in result["wikilinks_inserted"]
        note = adapter.read_file(result["path"])
        assert "[[Spaced Repetition]]" in note

    def test_auto_link_disabled(self):
        """No wikilinks inserted when auto_link=False."""
        existing = frontmatter.dumps(frontmatter.Post("body", title="Spaced Repetition"))
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({
            "notes/spaced-repetition.md": existing,
            "captures/c.md": cap,
        })

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="Learning",
            summary="About spaced repetition.",
            domain="learning",
            content="Spaced repetition is great.",
            auto_link=False,
        )

        assert result["wikilinks_inserted"] == []

    def test_own_title_not_linked(self):
        """The note's own title is excluded from auto-linking."""
        existing = frontmatter.dumps(frontmatter.Post("body", title="Testing"))
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({
            "notes/testing.md": existing,
            "captures/c.md": cap,
        })

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="Testing",
            summary="About testing.",
            domain="eng",
            content="Testing is important.",
        )

        # Should not self-link
        assert "Testing" not in result["wikilinks_inserted"]


# ---------------------------------------------------------------------------
# Metadata & frontmatter
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_confidence_default(self):
        """Default confidence is 0.7."""
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({"captures/c.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="T",
            summary="S.",
            domain="d",
            content="C.",
        )

        post = frontmatter.loads(adapter.read_file(result["path"]))
        assert post.metadata["confidence"] == 0.7

    def test_custom_confidence(self):
        """Custom confidence is stored in frontmatter."""
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({"captures/c.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="T",
            summary="S.",
            domain="d",
            content="C.",
            confidence=0.95,
        )

        post = frontmatter.loads(adapter.read_file(result["path"]))
        assert post.metadata["confidence"] == 0.95

    def test_aliases_stored(self):
        """Aliases appear in note frontmatter."""
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({"captures/c.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="T",
            summary="S.",
            domain="d",
            content="C.",
            aliases=["Alt Name", "Another"],
        )

        post = frontmatter.loads(adapter.read_file(result["path"]))
        assert post.metadata["aliases"] == ["Alt Name", "Another"]

    def test_promoted_from_in_frontmatter(self):
        """promoted_from lists source capture paths in note frontmatter."""
        cap = make_capture("C", "B.", tags=[])
        adapter, promote = setup_promote({"captures/c.md": cap})

        result = promote(
            action="promote",
            capture_paths=["captures/c.md"],
            title="T",
            summary="S.",
            domain="d",
            content="C.",
        )

        post = frontmatter.loads(adapter.read_file(result["path"]))
        assert post.metadata["promoted_from"] == ["captures/c.md"]


# ---------------------------------------------------------------------------
# Capture delete tests
# ---------------------------------------------------------------------------


def setup_capture(files: dict[str, str] | None = None):
    """Register write tools against a MemoryAdapter and return (adapter, vault_capture)."""
    adapter = MemoryAdapter(files)
    mcp = McpStub()
    register_write_tools(mcp, adapter)
    return adapter, mcp.tools["vault_capture"]


class TestCaptureDelete:
    def test_delete_success(self):
        """Delete removes the file from the adapter."""
        cap = make_capture("To Delete", "Some text.", tags=["ai"])
        adapter, capture = setup_capture({"captures/cap1.md": cap})

        result = capture(action="delete", path="captures/cap1.md")

        assert result["status"] == "deleted"
        assert result["path"] == "captures/cap1.md"
        assert "captures/cap1.md" not in adapter.files

    def test_delete_returns_metadata(self):
        """Delete returns the deleted capture's title and tags."""
        cap = make_capture("My Title", "Insight.", tags=["ai", "llm"])
        adapter, capture = setup_capture({"captures/cap1.md": cap})

        result = capture(action="delete", path="captures/cap1.md")

        assert result["deleted_title"] == "My Title"
        assert sorted(result["deleted_tags"]) == ["ai", "llm"]

    def test_delete_not_found(self):
        """Error when file does not exist."""
        adapter, capture = setup_capture()

        result = capture(action="delete", path="captures/nonexistent.md")

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_delete_outside_captures(self):
        """Error when path is not under captures/."""
        cap = make_capture("Note", "Body.")
        adapter, capture = setup_capture({"notes/note.md": cap})

        result = capture(action="delete", path="notes/note.md")

        assert result["status"] == "error"
        assert "captures/" in result["message"]

    def test_unknown_action(self):
        """Unknown action error includes both save and delete."""
        adapter, capture = setup_capture()

        result = capture(action="unknown")

        assert result["status"] == "error"
        assert "save" in result["message"]
        assert "delete" in result["message"]

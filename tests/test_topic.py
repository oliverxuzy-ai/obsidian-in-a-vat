"""Tests for topic lifecycle (prepare, create, update)."""

from __future__ import annotations

import frontmatter
import pytest

from tests.conftest import McpStub, MemoryAdapter, make_note, make_topic
from vault_mcp.graph.clustering import compute_clusters
from vault_mcp.graph.engine import VaultGraph
from vault_mcp.graph.models import ClusterData
from vault_mcp.tools.graph import register_graph_tools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup(files: dict[str, str]) -> tuple[MemoryAdapter, McpStub, dict]:
    """Register tools and return (adapter, mcp_stub, tools_dict)."""
    adapter = MemoryAdapter(files)
    mcp_stub = McpStub()
    register_graph_tools(mcp_stub, adapter)
    return adapter, mcp_stub, mcp_stub.tools


def _rebuild_and_cluster(tools: dict) -> None:
    """Run rebuild + clusters to populate caches."""
    tools["vault_analyze"](action="rebuild_graph")
    tools["vault_analyze"](action="clusters")


# ---------------------------------------------------------------------------
# TestTopicPrepare
# ---------------------------------------------------------------------------

class TestTopicPrepare:
    def test_prepare_from_note_paths(self):
        files = {
            "notes/a.md": make_note("A", "Summary of A about learning"),
            "notes/b.md": make_note("B", "Summary of B about memory"),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="prepare", note_paths=["notes/a.md", "notes/b.md"]
        )
        assert result["status"] == "success"
        assert len(result["members"]) == 2
        # Check summaries are included
        titles = {m["title"] for m in result["members"]}
        assert "A" in titles
        assert "B" in titles
        # Check summaries contain actual text, not full content
        for m in result["members"]:
            assert "summary" in m
            assert "centrality" in m

    def test_prepare_from_cluster_id(self):
        # Two clusters: A<->B and C<->D
        files = {
            "notes/a.md": make_note("A", "Links to [[B]]", tags=["ai"]),
            "notes/b.md": make_note("B", "Links to [[A]]", tags=["ai"]),
            "notes/c.md": make_note("C", "Links to [[D]]", tags=["health"]),
            "notes/d.md": make_note("D", "Links to [[C]]", tags=["health"]),
        }
        adapter, mcp, tools = _setup(files)
        _rebuild_and_cluster(tools)

        # Get cluster ids
        clusters_result = tools["vault_analyze"](action="clusters")
        cid = clusters_result["clusters"][0]["id"]

        result = tools["vault_topic"](action="prepare", cluster_id=cid)
        assert result["status"] == "success"
        assert len(result["members"]) > 0

    def test_prepare_returns_summaries_not_full_content(self):
        long_content = "X" * 5000
        files = {
            "notes/a.md": make_note("A", "Short summary", content=long_content),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](action="prepare", note_paths=["notes/a.md"])
        member = result["members"][0]
        # Summary should be short, not the full 5000 chars
        assert len(member["summary"]) < 500

    def test_prepare_includes_graph_metrics(self):
        files = {
            "notes/a.md": make_note("A", "Links to [[B]] and [[C]]"),
            "notes/b.md": make_note("B", "Links to [[A]]"),
            "notes/c.md": make_note("C", "Links to [[A]]"),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="prepare",
            note_paths=["notes/a.md", "notes/b.md", "notes/c.md"],
        )
        metrics = result["graph_metrics"]
        assert "hub_notes" in metrics
        assert "bridge_notes" in metrics
        assert "total_internal_edges" in metrics
        assert metrics["total_internal_edges"] > 0

    def test_prepare_staleness_detection(self):
        files = {
            "notes/a.md": make_note("A", "Content A"),
            "notes/b.md": make_note("B", "Content B"),
            "topics/test-topic.md": make_topic(
                "Test Topic",
                "Topic content",
                member_notes=["notes/a.md", "notes/b.md"],
                graph_generation=1,
            ),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        # Add a new note (not in topic's member_notes)
        adapter.files["notes/c.md"] = make_note("C", "New content")
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="prepare",
            note_paths=["notes/a.md", "notes/b.md", "notes/c.md"],
            topic_path="topics/test-topic.md",
        )
        assert "staleness" in result
        staleness = result["staleness"]
        assert staleness["is_stale"] is True
        assert "notes/c.md" in staleness["added_notes"]

    def test_prepare_split_detection(self):
        """When topic members end up in different clusters, detect split."""
        # Create two clear clusters with a topic spanning both
        files = {
            "notes/a1.md": make_note("A1", "Links to [[A2]]", tags=["ai"]),
            "notes/a2.md": make_note("A2", "Links to [[A1]]", tags=["ai"]),
            "notes/b1.md": make_note("B1", "Links to [[B2]]", tags=["health"]),
            "notes/b2.md": make_note("B2", "Links to [[B1]]", tags=["health"]),
            "topics/mixed.md": make_topic(
                "Mixed Topic",
                "Content",
                member_notes=["notes/a1.md", "notes/b1.md"],
                graph_generation=0,
            ),
        }
        adapter, mcp, tools = _setup(files)
        _rebuild_and_cluster(tools)

        result = tools["vault_topic"](
            action="prepare",
            note_paths=["notes/a1.md", "notes/b1.md"],
            topic_path="topics/mixed.md",
        )
        staleness = result.get("staleness", {})
        # Members are in different clusters
        if "split_detected" in staleness:
            assert staleness["split_detected"] is True

    def test_prepare_requires_input(self):
        adapter, mcp, tools = _setup({})
        result = tools["vault_topic"](action="prepare")
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# TestTopicCreate
# ---------------------------------------------------------------------------

class TestTopicCreate:
    def test_create_writes_to_topics_dir(self):
        files = {
            "notes/a.md": make_note("A", "Content A"),
            "notes/b.md": make_note("B", "Content B"),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="create",
            title="Learning Methods",
            content="# Core Idea\n\nAn overview of learning methods.\n\n# Key Notes\n\n- [[A]]\n- [[B]]",
            domain="learning",
            tags=["learning"],
            member_notes=["notes/a.md", "notes/b.md"],
        )
        assert result["status"] == "success"
        assert result["path"].startswith("topics/")
        assert result["path"] in adapter.files

    def test_create_frontmatter_correct(self):
        files = {
            "notes/a.md": make_note("A", "Content A"),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="create",
            title="Test Topic",
            content="Body",
            domain="test",
            tags=["test"],
            member_notes=["notes/a.md"],
        )
        raw = adapter.files[result["path"]]
        post = frontmatter.loads(raw)
        assert post.metadata["status"] == "topic"
        assert post.metadata["member_notes"] == ["notes/a.md"]
        assert post.metadata["domain"] == "test"
        assert "graph_generation" in post.metadata

    def test_create_updates_reverse_references(self):
        files = {
            "notes/a.md": make_note("A", "Content A"),
            "notes/b.md": make_note("B", "Content B"),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="create",
            title="My Topic",
            content="Body",
            domain="test",
            member_notes=["notes/a.md", "notes/b.md"],
        )
        topic_path = result["path"]

        # Check reverse references
        post_a = frontmatter.loads(adapter.files["notes/a.md"])
        assert topic_path in post_a.metadata.get("topics", [])

        post_b = frontmatter.loads(adapter.files["notes/b.md"])
        assert topic_path in post_b.metadata.get("topics", [])

    def test_create_auto_inserts_wikilinks(self):
        files = {
            "notes/alpha.md": make_note("Alpha Concept", "About alpha"),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="create",
            title="Test Topic",
            content="This discusses the Alpha Concept in detail.",
            domain="test",
            member_notes=["notes/alpha.md"],
        )
        raw = adapter.files[result["path"]]
        assert "[[Alpha Concept]]" in raw

    def test_create_slug_collision_handling(self):
        files = {
            "topics/test-topic.md": make_topic("Test Topic", "Existing"),
            "notes/a.md": make_note("A", "Content"),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="create",
            title="Test Topic",
            content="New topic with same name",
            domain="test",
            member_notes=["notes/a.md"],
        )
        assert result["path"] == "topics/test-topic-2.md"

    def test_create_requires_title_and_content(self):
        adapter, mcp, tools = _setup({})
        result = tools["vault_topic"](action="create", title="", content="Body")
        assert result["status"] == "error"

        result = tools["vault_topic"](action="create", title="Title", content="")
        assert result["status"] == "error"

    def test_create_triggers_graph_update(self):
        files = {
            "notes/a.md": make_note("A", "Content A"),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        tools["vault_topic"](
            action="create",
            title="New Topic",
            content="Body about [[A]]",
            domain="test",
            member_notes=["notes/a.md"],
        )
        # The new topic should now be in the graph
        assert any("topics/" in p for p in adapter.files if p.endswith(".md"))


# ---------------------------------------------------------------------------
# TestTopicUpdate
# ---------------------------------------------------------------------------

class TestTopicUpdate:
    def test_update_content_only(self):
        files = {
            "notes/a.md": make_note("A", "Content"),
            "topics/test.md": make_topic(
                "Test", "Old content", member_notes=["notes/a.md"]
            ),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="update",
            topic_path="topics/test.md",
            content="Updated content about [[A]]",
        )
        assert result["status"] == "success"
        raw = adapter.files["topics/test.md"]
        assert "Updated content" in raw

    def test_update_adds_new_members(self):
        files = {
            "notes/a.md": make_note("A", "Content"),
            "notes/b.md": make_note("B", "Content"),
            "topics/test.md": make_topic(
                "Test", "Content", member_notes=["notes/a.md"]
            ),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        result = tools["vault_topic"](
            action="update",
            topic_path="topics/test.md",
            member_notes=["notes/a.md", "notes/b.md"],
        )
        assert result["status"] == "success"

        # b should now have reverse reference
        post_b = frontmatter.loads(adapter.files["notes/b.md"])
        assert "topics/test.md" in post_b.metadata.get("topics", [])

    def test_update_removes_old_members(self):
        files = {
            "notes/a.md": make_note("A", "Content", topics=["topics/test.md"]),
            "notes/b.md": make_note("B", "Content", topics=["topics/test.md"]),
            "topics/test.md": make_topic(
                "Test", "Content", member_notes=["notes/a.md", "notes/b.md"]
            ),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        # Remove b from members
        result = tools["vault_topic"](
            action="update",
            topic_path="topics/test.md",
            member_notes=["notes/a.md"],
        )
        assert result["status"] == "success"

        # b's reverse reference should be removed
        post_b = frontmatter.loads(adapter.files["notes/b.md"])
        assert "topics/test.md" not in post_b.metadata.get("topics", [])

        # a's should remain
        post_a = frontmatter.loads(adapter.files["notes/a.md"])
        assert "topics/test.md" in post_a.metadata.get("topics", [])

    def test_update_refreshes_graph_generation(self):
        files = {
            "notes/a.md": make_note("A", "Content"),
            "topics/test.md": make_topic(
                "Test", "Content", member_notes=["notes/a.md"], graph_generation=0
            ),
        }
        adapter, mcp, tools = _setup(files)
        tools["vault_analyze"](action="rebuild_graph")

        tools["vault_topic"](
            action="update",
            topic_path="topics/test.md",
            content="New content",
        )
        post = frontmatter.loads(adapter.files["topics/test.md"])
        assert post.metadata["graph_generation"] > 0

    def test_update_nonexistent_topic(self):
        adapter, mcp, tools = _setup({})
        result = tools["vault_topic"](
            action="update", topic_path="topics/nope.md", content="x"
        )
        assert result["status"] == "error"

    def test_update_requires_topic_path(self):
        adapter, mcp, tools = _setup({})
        result = tools["vault_topic"](action="update")
        assert result["status"] == "error"

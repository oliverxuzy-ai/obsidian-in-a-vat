"""Tests for the knowledge graph engine."""

from __future__ import annotations

import json

import pytest

from tests.conftest import MemoryAdapter, make_capture, make_note
from vault_mcp.graph.clustering import compute_clusters
from vault_mcp.graph.engine import VaultGraph
from vault_mcp.graph.models import ClusterData, GraphData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_graph(files: dict[str, str]) -> VaultGraph:
    adapter = MemoryAdapter(files)
    vg = VaultGraph(adapter)
    vg.rebuild()
    return vg


# ---------------------------------------------------------------------------
# TestGraphRebuild
# ---------------------------------------------------------------------------

class TestGraphRebuild:
    def test_empty_vault(self):
        vg = _build_graph({})
        assert vg.g.number_of_nodes() == 0
        assert vg.g.number_of_edges() == 0

    def test_single_note_no_links(self):
        files = {
            "notes/alpha.md": make_note("Alpha", "Alpha is a concept"),
        }
        vg = _build_graph(files)
        assert vg.g.number_of_nodes() == 1
        assert vg.g.number_of_edges() == 0
        assert "notes/alpha.md" in vg.g

    def test_two_notes_mutual_links(self):
        files = {
            "notes/alpha.md": make_note(
                "Alpha", "Alpha relates to [[Beta]]"
            ),
            "notes/beta.md": make_note(
                "Beta", "Beta relates to [[Alpha]]"
            ),
        }
        vg = _build_graph(files)
        assert vg.g.number_of_nodes() == 2
        assert vg.g.number_of_edges() == 2
        assert vg.g.has_edge("notes/alpha.md", "notes/beta.md")
        assert vg.g.has_edge("notes/beta.md", "notes/alpha.md")

    def test_unresolved_wikilink_ignored(self):
        files = {
            "notes/alpha.md": make_note(
                "Alpha", "Links to [[NonExistent]]"
            ),
        }
        vg = _build_graph(files)
        assert vg.g.number_of_nodes() == 1
        assert vg.g.number_of_edges() == 0

    def test_alias_resolution(self):
        files = {
            "notes/spaced-repetition.md": make_note(
                "Spaced Repetition",
                "A learning method",
                aliases=["SRS"],
            ),
            "notes/anki.md": make_note(
                "Anki",
                "Anki uses [[SRS]] to schedule reviews",
            ),
        }
        vg = _build_graph(files)
        assert vg.g.has_edge("notes/anki.md", "notes/spaced-repetition.md")

    def test_captures_excluded(self):
        files = {
            "captures/2026-01-01-000000-test.md": make_capture(
                "Test", "A capture"
            ),
            "notes/alpha.md": make_note("Alpha", "A note"),
        }
        vg = _build_graph(files)
        assert vg.g.number_of_nodes() == 1
        assert "captures/2026-01-01-000000-test.md" not in vg.g

    def test_topics_included(self):
        files = {
            "notes/alpha.md": make_note("Alpha", "A note about [[Learning Topic]]"),
            "topics/learning.md": make_note(
                "Learning Topic", "Topic about learning and [[Alpha]]"
            ),
        }
        vg = _build_graph(files)
        assert vg.g.number_of_nodes() == 2
        assert "topics/learning.md" in vg.g

    def test_rebuild_returns_stats(self):
        files = {
            "notes/a.md": make_note("A", "Note A links to [[B]]"),
            "notes/b.md": make_note("B", "Note B"),
        }
        vg = VaultGraph(MemoryAdapter(files))
        result = vg.rebuild()
        assert result["status"] == "success"
        assert result["nodes"] == 2
        assert result["edges"] == 1
        assert "elapsed_ms" in result

    def test_filename_stem_resolution(self):
        """Wikilink [[foo bar]] should resolve to notes/foo-bar.md via stem."""
        files = {
            "notes/foo-bar.md": make_note("Unrelated Title", "Content"),
            "notes/other.md": make_note("Other", "Links to [[foo bar]]"),
        }
        vg = _build_graph(files)
        assert vg.g.has_edge("notes/other.md", "notes/foo-bar.md")


# ---------------------------------------------------------------------------
# TestIncrementalUpdate
# ---------------------------------------------------------------------------

class TestIncrementalUpdate:
    def test_unchanged_file_not_reparsed(self):
        files = {"notes/a.md": make_note("A", "Content A")}
        adapter = MemoryAdapter(files)
        vg = VaultGraph(adapter)
        vg.rebuild()
        gen_before = vg.generation

        result = vg.incremental_update()
        assert result["added"] == 0
        assert result["updated"] == 0
        assert result["removed"] == 0
        # Generation still increments even on no-op? No — check:
        # Actually per the algorithm, if nothing changed we return early without incrementing
        assert result["total_nodes"] == 1

    def test_modified_file_updates_edges(self):
        files = {
            "notes/a.md": make_note("A", "Content A"),
            "notes/b.md": make_note("B", "Content B"),
        }
        adapter = MemoryAdapter(files)
        vg = VaultGraph(adapter)
        vg.rebuild()
        assert vg.g.number_of_edges() == 0

        # Modify a to link to b
        adapter.files["notes/a.md"] = make_note("A", "Now links to [[B]]")
        result = vg.incremental_update()
        assert result["updated"] == 1
        assert vg.g.has_edge("notes/a.md", "notes/b.md")

    def test_deleted_file_removed(self):
        files = {
            "notes/a.md": make_note("A", "Content A"),
            "notes/b.md": make_note("B", "Content B"),
        }
        adapter = MemoryAdapter(files)
        vg = VaultGraph(adapter)
        vg.rebuild()
        assert vg.g.number_of_nodes() == 2

        del adapter.files["notes/b.md"]
        result = vg.incremental_update()
        assert result["removed"] == 1
        assert "notes/b.md" not in vg.g

    def test_new_file_added(self):
        files = {"notes/a.md": make_note("A", "Content A")}
        adapter = MemoryAdapter(files)
        vg = VaultGraph(adapter)
        vg.rebuild()

        adapter.files["notes/b.md"] = make_note("B", "Content B")
        result = vg.incremental_update()
        assert result["added"] == 1
        assert "notes/b.md" in vg.g

    def test_generation_increments(self):
        files = {"notes/a.md": make_note("A", "Content A")}
        adapter = MemoryAdapter(files)
        vg = VaultGraph(adapter)
        vg.rebuild()
        gen1 = vg.generation

        adapter.files["notes/b.md"] = make_note("B", "Content B")
        vg.incremental_update()
        assert vg.generation == gen1 + 1


# ---------------------------------------------------------------------------
# TestConnections
# ---------------------------------------------------------------------------

class TestConnections:
    def test_direct_neighbors(self):
        files = {
            "notes/a.md": make_note("A", "Links to [[B]]"),
            "notes/b.md": make_note("B", "Links to [[C]]"),
            "notes/c.md": make_note("C", "Standalone"),
        }
        vg = _build_graph(files)
        result = vg.get_connections("notes/a.md", depth=1)
        assert result["status"] == "success"
        paths = {n["path"] for n in result["subgraph"]["nodes"]}
        assert "notes/a.md" in paths
        assert "notes/b.md" in paths
        # c is 2 hops away
        assert "notes/c.md" not in paths

    def test_depth_2_two_hops(self):
        files = {
            "notes/a.md": make_note("A", "Links to [[B]]"),
            "notes/b.md": make_note("B", "Links to [[C]]"),
            "notes/c.md": make_note("C", "Standalone"),
        }
        vg = _build_graph(files)
        result = vg.get_connections("notes/a.md", depth=2)
        paths = {n["path"] for n in result["subgraph"]["nodes"]}
        assert "notes/c.md" in paths

    def test_limit_caps_results(self):
        # Create a star graph: center links to many leaves
        files = {"notes/center.md": make_note("Center", " ".join(f"[[Leaf{i}]]" for i in range(20)))}
        for i in range(20):
            files[f"notes/leaf{i}.md"] = make_note(f"Leaf{i}", "A leaf")
        vg = _build_graph(files)
        result = vg.get_connections("notes/center.md", depth=1, limit=5)
        assert len(result["subgraph"]["nodes"]) <= 5

    def test_common_neighbor_recommendations(self):
        # A->B, A->C, D->B, D->C => D is recommended for A (2 shared neighbors)
        files = {
            "notes/a.md": make_note("A", "Links to [[B]] and [[C]]"),
            "notes/b.md": make_note("B", "Node B"),
            "notes/c.md": make_note("C", "Node C"),
            "notes/d.md": make_note("D", "Links to [[B]] and [[C]]"),
        }
        vg = _build_graph(files)
        result = vg.get_connections("notes/a.md", depth=1)
        rec_paths = {r["path"] for r in result["recommendations"]}
        assert "notes/d.md" in rec_paths

    def test_nonexistent_node_error(self):
        vg = _build_graph({"notes/a.md": make_note("A", "Content")})
        result = vg.get_connections("notes/nope.md")
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# TestOrphans
# ---------------------------------------------------------------------------

class TestOrphans:
    def test_orphan_detected(self):
        files = {
            "notes/linked.md": make_note("Linked", "Links to [[Other]]"),
            "notes/other.md": make_note("Other", "Has inbound link"),
            "notes/orphan.md": make_note("Orphan", "No links at all"),
        }
        vg = _build_graph(files)
        result = vg.get_orphans()
        orphan_paths = {o["path"] for o in result["orphans"]}
        assert "notes/orphan.md" in orphan_paths
        assert "notes/linked.md" not in orphan_paths

    def test_linked_note_not_orphan(self):
        files = {
            "notes/a.md": make_note("A", "Links to [[B]]"),
            "notes/b.md": make_note("B", "Content"),
        }
        vg = _build_graph(files)
        result = vg.get_orphans()
        assert result["total"] == 0

    def test_pagination(self):
        files = {f"notes/orphan{i}.md": make_note(f"Orphan{i}", "No links") for i in range(10)}
        vg = _build_graph(files)
        result = vg.get_orphans(limit=3, offset=0)
        assert len(result["orphans"]) == 3
        assert result["total"] == 10

        result2 = vg.get_orphans(limit=3, offset=3)
        assert len(result2["orphans"]) == 3
        # No overlap
        paths1 = {o["path"] for o in result["orphans"]}
        paths2 = {o["path"] for o in result2["orphans"]}
        assert not paths1 & paths2


# ---------------------------------------------------------------------------
# TestClusters
# ---------------------------------------------------------------------------

class TestClusters:
    def test_two_disconnected_clusters(self):
        # Cluster 1: A <-> B, Cluster 2: C <-> D
        files = {
            "notes/a.md": make_note("A", "Links to [[B]]", tags=["ai"]),
            "notes/b.md": make_note("B", "Links to [[A]]", tags=["ai"]),
            "notes/c.md": make_note("C", "Links to [[D]]", tags=["health"]),
            "notes/d.md": make_note("D", "Links to [[C]]", tags=["health"]),
        }
        vg = _build_graph(files)
        result = compute_clusters(vg)
        assert len(result.clusters) == 2

    def test_cluster_labels(self):
        files = {
            "notes/a.md": make_note("A", "Links to [[B]]", tags=["ai", "llm"]),
            "notes/b.md": make_note("B", "Links to [[A]]", tags=["ai"]),
        }
        vg = _build_graph(files)
        result = compute_clusters(vg)
        assert len(result.clusters) >= 1
        assert result.clusters[0].label == "ai"

    def test_cached_reuse(self):
        files = {
            "notes/a.md": make_note("A", "Links to [[B]]"),
            "notes/b.md": make_note("B", "Links to [[A]]"),
        }
        vg = _build_graph(files)
        result1 = compute_clusters(vg)
        assert result1.graph_generation == vg.generation

        # Same generation => cache is valid
        result2 = compute_clusters(vg)
        assert result2.graph_generation == result1.graph_generation

    def test_stale_recompute(self):
        files = {
            "notes/a.md": make_note("A", "Content"),
        }
        adapter = MemoryAdapter(files)
        vg = VaultGraph(adapter)
        vg.rebuild()
        result1 = compute_clusters(vg)
        gen1 = result1.graph_generation

        adapter.files["notes/b.md"] = make_note("B", "Content")
        vg.incremental_update()
        result2 = compute_clusters(vg)
        assert result2.graph_generation > gen1

    def test_empty_graph_no_clusters(self):
        vg = _build_graph({})
        result = compute_clusters(vg)
        assert len(result.clusters) == 0


# ---------------------------------------------------------------------------
# TestSerialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_save_load_roundtrip(self):
        files = {
            "notes/a.md": make_note("A", "Links to [[B]]", tags=["ai"]),
            "notes/b.md": make_note("B", "Content", aliases=["Beta"]),
        }
        adapter = MemoryAdapter(files)
        vg = VaultGraph(adapter)
        vg.rebuild()

        # Load in a fresh VaultGraph
        vg2 = VaultGraph(adapter)
        vg2.load()
        assert vg2.g.number_of_nodes() == 2
        assert vg2.g.number_of_edges() == 1
        assert vg2.generation == vg.generation

    def test_missing_file_empty_graph(self):
        adapter = MemoryAdapter()
        vg = VaultGraph(adapter)
        vg.load()
        assert vg._loaded
        assert vg.g.number_of_nodes() == 0

    def test_corrupt_file_triggers_fresh_start(self):
        adapter = MemoryAdapter({".brain/graph.json": "not valid json!!!"})
        vg = VaultGraph(adapter)
        vg.load()
        assert vg._loaded
        assert vg.g.number_of_nodes() == 0


# ---------------------------------------------------------------------------
# TestSummaryExtraction
# ---------------------------------------------------------------------------

class TestSummaryExtraction:
    def test_extract_summary_from_note(self):
        files = {
            "notes/a.md": make_note("A", "This is the summary of A", content="Detailed content"),
        }
        vg = _build_graph(files)
        summary = vg.get_summary("notes/a.md")
        assert "This is the summary of A" in summary

    def test_missing_summary_returns_empty(self):
        """A file with no # Summary heading returns empty string."""
        from tests.conftest import MemoryAdapter
        import frontmatter

        content = frontmatter.dumps(frontmatter.Post("Just body text, no headings", title="X", status="note"))
        files = {"notes/x.md": content}
        vg = _build_graph(files)
        summary = vg.get_summary("notes/x.md")
        assert summary == ""

    def test_nonexistent_file_returns_empty(self):
        vg = _build_graph({})
        summary = vg.get_summary("notes/nope.md")
        assert summary == ""

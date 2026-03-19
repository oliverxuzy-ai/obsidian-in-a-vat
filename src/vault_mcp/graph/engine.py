"""Knowledge graph engine: build, update, query, serialize."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import Counter
from datetime import datetime, timezone

import frontmatter
import networkx as nx

from vault_mcp.adapters.base import StorageAdapter
from vault_mcp.graph.models import GraphData, GraphEdge, GraphNode
from vault_mcp.utils.markdown import extract_wikilinks

logger = logging.getLogger("vault-mcp.graph.engine")

GRAPH_PATH = ".brain/graph.json"
SCAN_DIRS = ("notes", "topics")

_SUMMARY_RE = re.compile(
    r"^#\s+Summary\s*\n(.*?)(?=^#\s|\Z)", re.MULTILINE | re.DOTALL
)


class VaultGraph:
    """In-memory knowledge graph backed by .brain/graph.json."""

    def __init__(self, adapter: StorageAdapter) -> None:
        self.adapter = adapter
        self.g: nx.DiGraph = nx.DiGraph()
        self._node_hashes: dict[str, str] = {}  # path -> content_hash
        self._generation: int = 0
        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def generation(self) -> int:
        return self._generation

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load graph from .brain/graph.json. No-op if already loaded."""
        if self._loaded:
            return
        try:
            raw = self.adapter.read_file(GRAPH_PATH)
            data = GraphData.model_validate_json(raw)
        except FileNotFoundError:
            self._loaded = True
            return
        except Exception:
            logger.warning("Corrupt graph.json, starting fresh")
            self._loaded = True
            return

        self.g.clear()
        self._node_hashes.clear()
        for node in data.nodes:
            self.g.add_node(
                node.path,
                title=node.title,
                tags=node.tags,
                domain=node.domain,
                aliases=node.aliases,
            )
            self._node_hashes[node.path] = node.content_hash
        for edge in data.edges:
            if edge.source in self.g and edge.target in self.g:
                self.g.add_edge(edge.source, edge.target)
        self._generation = data.generation
        self._loaded = True

    def save(self) -> None:
        """Serialize graph to .brain/graph.json."""
        nodes = []
        for path, attrs in self.g.nodes(data=True):
            nodes.append(
                GraphNode(
                    path=path,
                    title=attrs.get("title", ""),
                    tags=attrs.get("tags", []),
                    domain=attrs.get("domain", ""),
                    aliases=attrs.get("aliases", []),
                    content_hash=self._node_hashes.get(path, ""),
                )
            )
        edges = [GraphEdge(source=s, target=t) for s, t in self.g.edges()]
        data = GraphData(
            nodes=nodes,
            edges=edges,
            generation=self._generation,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.adapter.write_file(GRAPH_PATH, data.model_dump_json(indent=2))

    # ------------------------------------------------------------------
    # Build / Update
    # ------------------------------------------------------------------

    def rebuild(self) -> dict:
        """Full rebuild: scan all notes/ and topics/ files."""
        start = time.monotonic()
        self.g.clear()
        self._node_hashes.clear()

        files = self._scan_directories()
        all_file_data: list[tuple[str, str]] = []  # (path, content)
        for path in files:
            try:
                content = self.adapter.read_file(path)
                all_file_data.append((path, content))
            except Exception:
                logger.warning("Failed to read %s, skipping", path)

        # First pass: add all nodes (need title_map for edge resolution)
        for path, content in all_file_data:
            node = self._parse_node(path, content)
            self.g.add_node(
                path,
                title=node.title,
                tags=node.tags,
                domain=node.domain,
                aliases=node.aliases,
            )
            self._node_hashes[path] = node.content_hash

        # Build title_map for wikilink resolution
        title_map = self._build_title_map()

        # Second pass: add edges
        for path, content in all_file_data:
            targets = self._extract_link_targets(content)
            for target_title in targets:
                resolved = self._resolve_target(target_title, title_map)
                if resolved and resolved != path:
                    self.g.add_edge(path, resolved)

        self._generation += 1
        self._loaded = True
        self.save()

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "success",
            "nodes": self.g.number_of_nodes(),
            "edges": self.g.number_of_edges(),
            "elapsed_ms": elapsed_ms,
        }

    def incremental_update(self) -> dict:
        """Smart update: only re-parse files whose content hash changed."""
        self._ensure_loaded()
        start = time.monotonic()

        current_files = set(self._scan_directories())
        cached_paths = set(self._node_hashes.keys())

        removed = cached_paths - current_files
        added_count = 0
        updated_count = 0

        # Read all current files and detect changes
        changed: list[tuple[str, str, str]] = []  # (path, content, hash)
        for path in current_files:
            try:
                content = self.adapter.read_file(path)
            except Exception:
                logger.warning("Failed to read %s, skipping", path)
                continue
            h = hashlib.sha256(content.encode()).hexdigest()
            if path not in self._node_hashes:
                changed.append((path, content, h))
                added_count += 1
            elif self._node_hashes[path] != h:
                changed.append((path, content, h))
                updated_count += 1

        # Nothing changed
        if not removed and not changed:
            return {
                "status": "success",
                "added": 0,
                "updated": 0,
                "removed": 0,
                "total_nodes": self.g.number_of_nodes(),
                "total_edges": self.g.number_of_edges(),
            }

        # Remove deleted nodes
        for path in removed:
            if path in self.g:
                self.g.remove_node(path)
            self._node_hashes.pop(path, None)

        # Add/update changed nodes (first pass: nodes only)
        for path, content, h in changed:
            # Remove old edges if updating
            if path in self.g:
                self.g.remove_edges_from(list(self.g.in_edges(path)))
                self.g.remove_edges_from(list(self.g.out_edges(path)))

            node = self._parse_node(path, content)
            self.g.add_node(
                path,
                title=node.title,
                tags=node.tags,
                domain=node.domain,
                aliases=node.aliases,
            )
            self._node_hashes[path] = h

        # Rebuild title_map and re-resolve edges for changed files
        title_map = self._build_title_map()
        for path, content, _ in changed:
            targets = self._extract_link_targets(content)
            for target_title in targets:
                resolved = self._resolve_target(target_title, title_map)
                if resolved and resolved != path and resolved in self.g:
                    self.g.add_edge(path, resolved)

        self._generation += 1
        self.save()

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "success",
            "added": added_count,
            "updated": updated_count,
            "removed": len(removed),
            "total_nodes": self.g.number_of_nodes(),
            "total_edges": self.g.number_of_edges(),
            "elapsed_ms": elapsed_ms,
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_connections(
        self, path: str, depth: int = 1, limit: int = 50
    ) -> dict:
        """Return N-degree subgraph + common-neighbor recommendations."""
        self._ensure_loaded()

        if path not in self.g:
            return {"status": "error", "message": f"Node not found: {path}"}

        # BFS to collect nodes within depth
        visited: set[str] = {path}
        frontier: set[str] = {path}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for node in frontier:
                for neighbor in set(self.g.successors(node)) | set(
                    self.g.predecessors(node)
                ):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
            frontier = next_frontier

        # Build subgraph
        subgraph_nodes = sorted(visited)[:limit]
        subgraph_set = set(subgraph_nodes)
        nodes_out = []
        for n in subgraph_nodes:
            attrs = self.g.nodes[n]
            nodes_out.append(
                {
                    "path": n,
                    "title": attrs.get("title", ""),
                    "tags": attrs.get("tags", []),
                }
            )
        edges_out = [
            {"source": s, "target": t}
            for s, t in self.g.edges()
            if s in subgraph_set and t in subgraph_set
        ]

        # Common-neighbor recommendations
        undirected = self.g.to_undirected()
        direct_neighbors = set(undirected.neighbors(path))
        recommendations = []
        for candidate in self.g.nodes():
            if candidate == path or candidate in direct_neighbors:
                continue
            if candidate not in undirected:
                continue
            shared = direct_neighbors & set(undirected.neighbors(candidate))
            if len(shared) >= 2:
                attrs = self.g.nodes[candidate]
                recommendations.append(
                    {
                        "path": candidate,
                        "title": attrs.get("title", ""),
                        "shared_neighbors": len(shared),
                    }
                )
        recommendations.sort(key=lambda r: r["shared_neighbors"], reverse=True)

        return {
            "status": "success",
            "center": path,
            "subgraph": {"nodes": nodes_out, "edges": edges_out},
            "recommendations": recommendations[:10],
        }

    def get_orphans(self, limit: int = 50, offset: int = 0) -> dict:
        """Find notes with no inbound or outbound links."""
        self._ensure_loaded()

        orphans = []
        for node in self.g.nodes():
            if self.g.in_degree(node) == 0 and self.g.out_degree(node) == 0:
                attrs = self.g.nodes[node]
                orphans.append(
                    {
                        "path": node,
                        "title": attrs.get("title", ""),
                        "tags": attrs.get("tags", []),
                    }
                )
        orphans.sort(key=lambda o: o["path"])
        total = len(orphans)
        return {
            "status": "success",
            "orphans": orphans[offset : offset + limit],
            "total": total,
        }

    def get_summary(self, path: str) -> str:
        """Extract # Summary section from a note file."""
        try:
            content = self.adapter.read_file(path)
        except Exception:
            return ""
        post = frontmatter.loads(content)
        match = _SUMMARY_RE.search(post.content)
        if match:
            return match.group(1).strip()
        return ""

    def get_node_centrality(self, paths: list[str]) -> dict[str, float]:
        """Compute degree centrality for a subset of nodes."""
        self._ensure_loaded()
        if not self.g.nodes():
            return {}
        centrality = nx.degree_centrality(self.g)
        return {p: centrality.get(p, 0.0) for p in paths if p in self.g}

    def get_subgraph_metrics(self, paths: list[str]) -> dict:
        """Graph metrics for a set of nodes (used by topic prepare)."""
        self._ensure_loaded()
        path_set = set(paths) & set(self.g.nodes())
        if not path_set:
            return {
                "total_internal_edges": 0,
                "hub_notes": [],
                "bridge_notes": [],
                "edges": [],
            }

        sub = self.g.subgraph(path_set)

        # Internal edges
        edges = [{"source": s, "target": t} for s, t in sub.edges()]

        # Hub notes: highest degree in subgraph
        degrees = dict(sub.degree())
        sorted_by_degree = sorted(
            degrees.items(), key=lambda x: x[1], reverse=True
        )
        hub_notes = [p for p, _ in sorted_by_degree[:3] if degrees[p] > 0]

        # Bridge notes: highest betweenness in undirected subgraph
        bridge_notes: list[str] = []
        if len(path_set) >= 3:
            try:
                undirected_sub = sub.to_undirected()
                betweenness = nx.betweenness_centrality(undirected_sub)
                sorted_by_btw = sorted(
                    betweenness.items(), key=lambda x: x[1], reverse=True
                )
                bridge_notes = [
                    p for p, v in sorted_by_btw[:3] if v > 0
                ]
            except Exception:
                pass

        return {
            "total_internal_edges": len(edges),
            "hub_notes": hub_notes,
            "bridge_notes": bridge_notes,
            "edges": edges,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
            if not self.g.nodes():
                self.rebuild()

    def _scan_directories(self) -> list[str]:
        """List all .md files in notes/ and topics/."""
        files: list[str] = []
        for d in SCAN_DIRS:
            try:
                files.extend(self.adapter.list_files(d))
            except Exception:
                continue
        return files

    def _parse_node(self, path: str, content: str) -> GraphNode:
        """Parse frontmatter from a file into a GraphNode."""
        h = hashlib.sha256(content.encode()).hexdigest()
        try:
            post = frontmatter.loads(content)
            meta = post.metadata
        except Exception:
            return GraphNode(path=path, title="", content_hash=h)

        return GraphNode(
            path=path,
            title=meta.get("title", ""),
            tags=meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
            domain=meta.get("domain", ""),
            aliases=meta.get("aliases", []) if isinstance(meta.get("aliases"), list) else [],
            content_hash=h,
        )

    def _extract_link_targets(self, content: str) -> list[str]:
        """Extract wikilink target strings from content."""
        post = frontmatter.loads(content)
        links = extract_wikilinks(post.content)
        return [link["target"] for link in links]

    def _build_title_map(self) -> dict[str, str]:
        """Build lowercase title/alias -> path mapping from current graph."""
        title_map: dict[str, str] = {}
        for path, attrs in self.g.nodes(data=True):
            title = attrs.get("title", "")
            if title:
                title_map[title.lower()] = path
            for alias in attrs.get("aliases", []):
                alias_str = str(alias)
                if alias_str:
                    title_map[alias_str.lower()] = path
            # Filename stem as fallback: "notes/foo-bar.md" -> "foo bar"
            stem = path.rsplit("/", 1)[-1].removesuffix(".md")
            readable = stem.replace("-", " ")
            if readable.lower() not in title_map:
                title_map[readable.lower()] = path
        return title_map

    def _resolve_target(
        self, target_title: str, title_map: dict[str, str]
    ) -> str | None:
        """Resolve a wikilink target to a file path."""
        return title_map.get(target_title.lower())

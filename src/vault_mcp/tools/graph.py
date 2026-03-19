"""Graph analysis and topic lifecycle tools."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import frontmatter

from vault_mcp.adapters.base import StorageAdapter
from vault_mcp.graph.clustering import compute_clusters
from vault_mcp.graph.engine import VaultGraph
from vault_mcp.graph.models import ClusterData
from vault_mcp.utils.markdown import auto_insert_wikilinks, collect_note_titles

logger = logging.getLogger("vault-mcp.tools.graph")

CLUSTERS_PATH = ".brain/clusters.json"


def _generate_slug(*candidates: str) -> str:
    """Generate a URL-friendly slug from the first candidate with ASCII words."""
    for candidate in candidates:
        words = re.findall(r"[a-zA-Z0-9]+", candidate.lower())[:5]
        if words:
            return "-".join(words)
    return "topic"


def register_graph_tools(mcp, adapter: StorageAdapter) -> None:
    vault_graph = VaultGraph(adapter)
    _clusters_cache: dict[str, ClusterData | None] = {"data": None}

    # ------------------------------------------------------------------
    # vault_analyze — read-only graph analysis
    # ------------------------------------------------------------------

    @mcp.tool(annotations={"readOnlyHint": True})
    def vault_analyze(
        action: str,
        path: str = "",
        depth: int = 1,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Analyze vault knowledge graph.

        Actions:
          rebuild_graph: Build or incrementally update the knowledge graph
            from notes/ and topics/. Returns node/edge counts.
          clusters: Run Louvain community detection. Cached if graph unchanged.
            params: limit, offset
          connections: Subgraph around a note + common-neighbor recommendations.
            params: path (required), depth (default 1), limit (default 50)
          orphans: Notes with no inbound or outbound links.
            params: limit (default 50), offset (default 0)
        """
        if action == "rebuild_graph":
            return _handle_rebuild(vault_graph)
        elif action == "clusters":
            return _handle_clusters(vault_graph, adapter, _clusters_cache, limit, offset)
        elif action == "connections":
            if not path:
                return {"status": "error", "message": "path is required for connections"}
            return vault_graph.get_connections(path, depth, limit)
        elif action == "orphans":
            return vault_graph.get_orphans(limit, offset)
        else:
            return {
                "status": "error",
                "message": f"Unknown action '{action}'. Valid: rebuild_graph, clusters, connections, orphans",
            }

    # ------------------------------------------------------------------
    # vault_topic — topic lifecycle
    # ------------------------------------------------------------------

    @mcp.tool(annotations={"readOnlyHint": False})
    def vault_topic(
        action: str,
        # prepare params
        cluster_id: int | None = None,
        note_paths: list[str] | None = None,
        topic_path: str = "",
        # create / update params
        title: str = "",
        content: str = "",
        domain: str = "",
        tags: list[str] | None = None,
        member_notes: list[str] | None = None,
        aliases: list[str] | None = None,
    ) -> dict:
        """Manage topic lifecycle: prepare materials, create, or update.

        Actions:
          prepare: Gather structured materials for topic creation/update.
            Uses progressive disclosure — returns summaries, not full content.
            params: cluster_id OR note_paths (pick one).
                    topic_path (optional, for staleness detection on update).
          create: Write a new topic to topics/.
            params: title, content (Claude-generated body), domain, tags,
                    member_notes, aliases
          update: Update an existing topic.
            params: topic_path (required), content (optional, new body),
                    member_notes (optional, updated list), tags (optional)

        WORKFLOW — Claude MUST follow these steps:
        1. PREPARE: Call with action="prepare" to get summaries + graph metrics.
        2. DEEP READ (optional): Use vault_read(action="get") for important notes.
        3. SYNTHESIZE: Write topic body (synthesis, not concatenation).
        4. CONFIRM: Present to user. Wait for approval.
        5. WRITE: Call with action="create" or action="update".
        """
        if action == "prepare":
            return _handle_prepare(
                vault_graph, adapter, _clusters_cache,
                cluster_id, note_paths, topic_path,
            )
        elif action == "create":
            return _handle_create(
                vault_graph, adapter,
                title, content, domain, tags, member_notes, aliases,
            )
        elif action == "update":
            return _handle_update(
                vault_graph, adapter,
                topic_path, content, member_notes, tags,
            )
        else:
            return {
                "status": "error",
                "message": f"Unknown action '{action}'. Valid: prepare, create, update",
            }


# ----------------------------------------------------------------------
# vault_analyze handlers
# ----------------------------------------------------------------------


def _handle_rebuild(vault_graph: VaultGraph) -> dict:
    vault_graph.load()
    if vault_graph.g.number_of_nodes() == 0:
        return vault_graph.rebuild()
    return vault_graph.incremental_update()


def _handle_clusters(
    vault_graph: VaultGraph,
    adapter: StorageAdapter,
    cache: dict,
    limit: int,
    offset: int,
) -> dict:
    vault_graph._ensure_loaded()

    # Try cached clusters
    cached = cache.get("data")
    if cached is None:
        try:
            raw = adapter.read_file(CLUSTERS_PATH)
            cached = ClusterData.model_validate_json(raw)
            cache["data"] = cached
        except Exception:
            cached = None

    # Recompute if stale or missing
    if cached is None or cached.graph_generation != vault_graph.generation:
        cached = compute_clusters(vault_graph)
        adapter.write_file(CLUSTERS_PATH, cached.model_dump_json(indent=2))
        cache["data"] = cached

    # Paginate
    clusters_out = []
    for c in cached.clusters[offset : offset + limit]:
        clusters_out.append(
            {
                "id": c.id,
                "label": c.label,
                "size": len(c.members),
                "members": c.members,
            }
        )
    return {
        "status": "success",
        "clusters": clusters_out,
        "total": len(cached.clusters),
    }


# ----------------------------------------------------------------------
# vault_topic handlers
# ----------------------------------------------------------------------


def _handle_prepare(
    vault_graph: VaultGraph,
    adapter: StorageAdapter,
    clusters_cache: dict,
    cluster_id: int | None,
    note_paths: list[str] | None,
    topic_path: str,
) -> dict:
    vault_graph._ensure_loaded()

    # Determine member paths
    if cluster_id is not None:
        # Get from clusters
        cached = clusters_cache.get("data")
        if cached is None:
            try:
                raw = adapter.read_file(CLUSTERS_PATH)
                cached = ClusterData.model_validate_json(raw)
                clusters_cache["data"] = cached
            except Exception:
                return {
                    "status": "error",
                    "message": "No clusters available. Run vault_analyze(action='clusters') first.",
                }
        matching = [c for c in cached.clusters if c.id == cluster_id]
        if not matching:
            return {
                "status": "error",
                "message": f"Cluster {cluster_id} not found.",
            }
        paths = matching[0].members
    elif note_paths:
        paths = note_paths
    else:
        return {
            "status": "error",
            "message": "Provide cluster_id or note_paths.",
        }

    # Collect summaries (progressive disclosure)
    members = []
    centrality = vault_graph.get_node_centrality(paths)
    for p in paths:
        attrs = vault_graph.g.nodes.get(p, {})
        summary = vault_graph.get_summary(p)
        members.append(
            {
                "path": p,
                "title": attrs.get("title", ""),
                "tags": attrs.get("tags", []),
                "domain": attrs.get("domain", ""),
                "summary": summary,
                "centrality": round(centrality.get(p, 0.0), 3),
            }
        )

    # Graph metrics for this subset
    graph_metrics = vault_graph.get_subgraph_metrics(paths)

    result: dict = {
        "status": "success",
        "members": members,
        "graph_metrics": graph_metrics,
    }

    # Staleness detection if topic_path provided
    if topic_path:
        staleness = _detect_staleness(
            vault_graph, adapter, clusters_cache, topic_path, paths,
        )
        result["staleness"] = staleness

    return result


def _detect_staleness(
    vault_graph: VaultGraph,
    adapter: StorageAdapter,
    clusters_cache: dict,
    topic_path: str,
    current_cluster_members: list[str],
) -> dict:
    """Detect how stale a topic is relative to current graph state."""
    try:
        raw = adapter.read_file(topic_path)
        post = frontmatter.loads(raw)
    except Exception:
        return {"error": f"Cannot read topic: {topic_path}"}

    old_members = set(post.metadata.get("member_notes", []))
    topic_gen = post.metadata.get("graph_generation", 0)
    current_members = set(current_cluster_members)

    added = sorted(current_members - old_members)
    removed = sorted(old_members - current_members)
    total_old = max(len(old_members), 1)
    change_ratio = round((len(added) + len(removed)) / total_old, 2)

    staleness: dict = {
        "is_stale": topic_gen != vault_graph.generation,
        "topic_generation": topic_gen,
        "current_generation": vault_graph.generation,
        "added_notes": added,
        "removed_notes": removed,
        "change_ratio": change_ratio,
    }

    # Cluster split/merge detection
    cached = clusters_cache.get("data")
    if cached and old_members:
        cluster_distribution: dict[int, list[str]] = {}
        for c in cached.clusters:
            for member in c.members:
                if member in old_members:
                    cluster_distribution.setdefault(c.id, []).append(member)
        if len(cluster_distribution) > 1:
            staleness["split_detected"] = True
            staleness["split_clusters"] = {
                str(cid): members
                for cid, members in cluster_distribution.items()
            }

    return staleness


def _handle_create(
    vault_graph: VaultGraph,
    adapter: StorageAdapter,
    title: str,
    content: str,
    domain: str,
    tags: list[str] | None,
    member_notes: list[str] | None,
    aliases: list[str] | None,
) -> dict:
    if not title:
        return {"status": "error", "message": "title is required"}
    if not content:
        return {"status": "error", "message": "content is required"}

    members = member_notes or []
    now = datetime.now(timezone.utc)
    iso_now = now.isoformat()

    # Generate slug with collision handling
    slug = _generate_slug(title)
    filename = f"topics/{slug}.md"
    counter = 2
    while True:
        try:
            adapter.read_file(filename)
            filename = f"topics/{slug}-{counter}.md"
            counter += 1
        except FileNotFoundError:
            break

    # Auto-insert wikilinks (title_map: lowercase -> original title)
    title_map = collect_note_titles(adapter)
    body, wikilinks_inserted = auto_insert_wikilinks(
        content, title_map, exclude_titles=[title.lower()]
    )

    # Build topic file (graph_generation placeholder, updated after incremental_update)
    metadata = {
        "title": title,
        "status": "topic",
        "created": iso_now,
        "updated": iso_now,
        "domain": domain,
        "tags": tags or [],
        "aliases": aliases or [],
        "member_notes": members,
        "graph_generation": 0,
    }
    post = frontmatter.Post(body, **metadata)
    adapter.write_file(filename, frontmatter.dumps(post))

    # Update reverse references on member notes
    _update_reverse_references(adapter, members, filename, add=True)

    # Trigger incremental graph update, then stamp the resulting generation
    vault_graph.incremental_update()
    post.metadata["graph_generation"] = vault_graph.generation
    adapter.write_file(filename, frontmatter.dumps(post))

    return {
        "status": "success",
        "path": filename,
        "title": title,
        "member_count": len(members),
        "wikilinks_inserted": wikilinks_inserted,
    }


def _handle_update(
    vault_graph: VaultGraph,
    adapter: StorageAdapter,
    topic_path: str,
    content: str | None,
    member_notes: list[str] | None,
    tags: list[str] | None,
) -> dict:
    if not topic_path:
        return {"status": "error", "message": "topic_path is required"}

    try:
        raw = adapter.read_file(topic_path)
        post = frontmatter.loads(raw)
    except FileNotFoundError:
        return {"status": "error", "message": f"Topic not found: {topic_path}"}

    now = datetime.now(timezone.utc)
    iso_now = now.isoformat()

    # Update member notes and reverse references
    if member_notes is not None:
        old_members = set(post.metadata.get("member_notes", []))
        new_members = set(member_notes)
        added = new_members - old_members
        removed = old_members - new_members

        if added:
            _update_reverse_references(adapter, list(added), topic_path, add=True)
        if removed:
            _update_reverse_references(adapter, list(removed), topic_path, add=False)

        post.metadata["member_notes"] = member_notes

    if content is not None:
        # Auto-insert wikilinks in new content
        title_map = collect_note_titles(adapter)
        title = post.metadata.get("title", "")
        body, _ = auto_insert_wikilinks(
            content, title_map, exclude_titles=[title.lower()] if title else [],
        )
        post.content = body

    if tags is not None:
        post.metadata["tags"] = tags

    post.metadata["updated"] = iso_now

    adapter.write_file(topic_path, frontmatter.dumps(post))

    # Trigger incremental graph update, then stamp the resulting generation
    vault_graph.incremental_update()
    post.metadata["graph_generation"] = vault_graph.generation
    adapter.write_file(topic_path, frontmatter.dumps(post))

    return {
        "status": "success",
        "path": topic_path,
        "title": post.metadata.get("title", ""),
        "member_count": len(post.metadata.get("member_notes", [])),
    }


def _update_reverse_references(
    adapter: StorageAdapter,
    note_paths: list[str],
    topic_path: str,
    add: bool,
) -> None:
    """Add or remove topic_path from notes' 'topics' frontmatter field."""
    for path in note_paths:
        try:
            raw = adapter.read_file(path)
            post = frontmatter.loads(raw)
        except Exception:
            continue

        topics_list = post.metadata.get("topics", [])
        if not isinstance(topics_list, list):
            topics_list = []

        if add:
            if topic_path not in topics_list:
                topics_list.append(topic_path)
        else:
            topics_list = [t for t in topics_list if t != topic_path]

        post.metadata["topics"] = topics_list
        adapter.write_file(path, frontmatter.dumps(post))

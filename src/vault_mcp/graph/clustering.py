"""Louvain community detection wrapper."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import community as community_louvain

from vault_mcp.graph.engine import VaultGraph
from vault_mcp.graph.models import Cluster, ClusterData


def compute_clusters(graph: VaultGraph) -> ClusterData:
    """Run Louvain community detection on the undirected projection."""
    if graph.g.number_of_nodes() == 0:
        return ClusterData(
            clusters=[],
            graph_generation=graph.generation,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    undirected = graph.g.to_undirected()
    partition = community_louvain.best_partition(undirected)

    # Group by cluster id
    clusters_map: dict[int, list[str]] = {}
    for node, cid in partition.items():
        clusters_map.setdefault(cid, []).append(node)

    clusters = []
    for cid, members in clusters_map.items():
        label = _infer_cluster_label(graph, members)
        clusters.append(
            Cluster(id=cid, label=label, members=sorted(members))
        )

    # Sort by size descending
    clusters.sort(key=lambda c: len(c.members), reverse=True)

    return ClusterData(
        clusters=clusters,
        graph_generation=graph.generation,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


def _infer_cluster_label(graph: VaultGraph, members: list[str]) -> str:
    """Pick the most frequent tag or domain across cluster members."""
    tag_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()

    for path in members:
        if path not in graph.g:
            continue
        attrs = graph.g.nodes[path]
        for tag in attrs.get("tags", []):
            tag_counter[tag] += 1
        domain = attrs.get("domain", "")
        if domain:
            domain_counter[domain] += 1

    # Prefer tags (more specific), fall back to domain
    if tag_counter:
        return tag_counter.most_common(1)[0][0]
    if domain_counter:
        return domain_counter.most_common(1)[0][0]
    return "unlabeled"

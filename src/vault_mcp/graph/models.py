"""Pydantic models for knowledge graph serialization."""

from __future__ import annotations

from pydantic import BaseModel


class GraphNode(BaseModel):
    path: str
    title: str
    tags: list[str] = []
    domain: str = ""
    aliases: list[str] = []
    content_hash: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphData(BaseModel):
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    generation: int = 0
    updated_at: str | None = None


class Cluster(BaseModel):
    id: int
    label: str
    members: list[str]


class ClusterData(BaseModel):
    clusters: list[Cluster] = []
    graph_generation: int = 0
    updated_at: str | None = None

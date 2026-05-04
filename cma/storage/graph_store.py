"""Build and inspect the memory graph from parsed MemoryRecord objects."""

import networkx as nx

from cma.schemas.memory_record import MemoryRecord


def build_graph(records: list[MemoryRecord]) -> nx.DiGraph:
    """Build a directed graph from memory records.

    Nodes are records keyed by record_id. Edges follow wikilinks. Wikilinks pointing
    to non-existent notes still create edges, with the target node marked exists=False
    so graph health checks can flag them as broken.

    Resolution order for a wikilink target:
      1. exact title match (case-insensitive)
      2. exact record_id (filename stem) match (case-insensitive)
      3. otherwise treated as a missing target
    """
    g: nx.DiGraph = nx.DiGraph()
    by_title: dict[str, str] = {}
    by_stem: dict[str, str] = {}

    for rec in records:
        g.add_node(
            rec.record_id,
            type=rec.type,
            title=rec.title,
            path=rec.path,
            status=rec.status,
            tags=list(rec.tags),
            confidence=rec.confidence,
            domain=rec.domain,
            exists=True,
        )
        by_title[rec.title.lower()] = rec.record_id
        by_stem[rec.record_id.lower()] = rec.record_id

    for rec in records:
        for link in rec.links:
            key = link.lower()
            target_id = by_title.get(key) or by_stem.get(key)
            if target_id is None:
                target_id = link
                if not g.has_node(target_id):
                    g.add_node(target_id, type="missing", title=link, exists=False)
            g.add_edge(rec.record_id, target_id, edge_type="wikilink")

    return g


def graph_health_report(g: nx.DiGraph) -> dict:
    """Return a structured health summary for the graph.

    Orphan rule: an existing node whose existing-node neighborhood (predecessors and
    successors restricted to exists=True nodes) is empty. A note that only links to
    missing notes is still considered an orphan because it cannot reach any real note.
    """
    nodes_existing = [n for n, d in g.nodes(data=True) if d.get("exists", False)]
    nodes_missing = [n for n, d in g.nodes(data=True) if not d.get("exists", False)]

    orphans: list[str] = []
    for n in nodes_existing:
        in_existing = any(g.nodes[s].get("exists", False) for s in g.predecessors(n))
        out_existing = any(g.nodes[t].get("exists", False) for t in g.successors(n))
        if not in_existing and not out_existing:
            orphans.append(n)

    broken_links: list[dict] = []
    for src, tgt in g.edges():
        if not g.nodes[tgt].get("exists", False):
            broken_links.append({"source": src, "target": tgt})

    type_counts: dict[str, int] = {}
    for _, d in g.nodes(data=True):
        if d.get("exists", False):
            t = d.get("type", "note")
            type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "total_nodes": len(nodes_existing),
        "missing_nodes": len(nodes_missing),
        "total_edges": g.number_of_edges(),
        "orphans": sorted(orphans),
        "broken_links": broken_links,
        "node_types": type_counts,
    }

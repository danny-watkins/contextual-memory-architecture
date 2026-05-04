"""Graph traversal with beam search and depth-limited expansion."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True)
class Candidate:
    """A node visited during traversal, tagged with the depth at which it was first seen."""

    node_id: str
    depth: int


def traverse(
    graph: nx.DiGraph,
    seeds: list[tuple[str, float]],
    max_depth: int = 2,
    beam_width: int = 5,
) -> list[Candidate]:
    """Beam-pruned BFS over outgoing and incoming edges.

    Args:
        graph: the memory graph (build_graph output).
        seeds: list of (record_id, seed_score) - the entry points.
        max_depth: how many hops to expand. 0 = seeds only.
        beam_width: at each depth, keep at most this many candidates by seed_score.

    Returns:
        A list of Candidate objects in the order they were first visited.
        Missing-target placeholder nodes (exists=False) are skipped.
    """
    if not seeds:
        return []

    # Filter seeds to those that exist in the graph as real nodes.
    real_seeds: list[tuple[str, float]] = []
    for nid, score in seeds:
        if graph.has_node(nid) and graph.nodes[nid].get("exists", False):
            real_seeds.append((nid, score))
    if not real_seeds:
        return []

    visited: dict[str, int] = {nid: 0 for nid, _ in real_seeds}
    results: list[Candidate] = [Candidate(nid, 0) for nid, _ in real_seeds]
    current_frontier: list[tuple[str, float]] = real_seeds

    for depth in range(1, max_depth + 1):
        next_candidates: dict[str, float] = {}
        for node_id, parent_score in current_frontier:
            for neighbor in _neighbors(graph, node_id):
                if neighbor in visited:
                    continue
                if not graph.nodes[neighbor].get("exists", False):
                    continue
                # Inherit parent score; deeper nodes get scored later with depth decay.
                if neighbor not in next_candidates or next_candidates[neighbor] < parent_score:
                    next_candidates[neighbor] = parent_score
        if not next_candidates:
            break
        # Beam-prune: keep top beam_width by inherited score.
        ranked = sorted(next_candidates.items(), key=lambda x: x[1], reverse=True)[
            :beam_width
        ]
        for nid, score in ranked:
            visited[nid] = depth
            results.append(Candidate(nid, depth))
        current_frontier = ranked

    return results


def _neighbors(graph: nx.DiGraph, node_id: str):
    """Yield both outgoing and incoming neighbors (treat backlinks symmetrically)."""
    seen = set()
    for n in graph.successors(node_id):
        if n not in seen:
            seen.add(n)
            yield n
    for n in graph.predecessors(node_id):
        if n not in seen:
            seen.add(n)
            yield n

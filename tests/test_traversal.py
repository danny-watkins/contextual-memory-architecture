from pathlib import Path

from cma.retriever.traversal import Candidate, traverse
from cma.storage.graph_store import build_graph
from cma.storage.markdown_store import parse_vault


def _build(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "A.md").write_text("# A\nLinks to [[B]] and [[C]].", encoding="utf-8")
    (vault / "B.md").write_text("# B\nLinks to [[D]].", encoding="utf-8")
    (vault / "C.md").write_text("# C\nNo links.", encoding="utf-8")
    (vault / "D.md").write_text("# D\nNo links.", encoding="utf-8")
    (vault / "E.md").write_text("# E\nIsolated note.", encoding="utf-8")
    return build_graph(parse_vault(vault))


def test_traverse_returns_seeds_at_depth_zero(tmp_path: Path):
    graph = _build(tmp_path)
    result = traverse(graph, [("A", 0.9)], max_depth=0, beam_width=5)
    assert result == [Candidate("A", 0)]


def test_traverse_expands_one_hop(tmp_path: Path):
    graph = _build(tmp_path)
    result = traverse(graph, [("A", 0.9)], max_depth=1, beam_width=5)
    ids = {c.node_id for c in result}
    assert "A" in ids
    assert "B" in ids
    assert "C" in ids
    assert "D" not in ids  # depth 2


def test_traverse_expands_two_hops(tmp_path: Path):
    graph = _build(tmp_path)
    result = traverse(graph, [("A", 0.9)], max_depth=2, beam_width=5)
    ids = {c.node_id for c in result}
    assert {"A", "B", "C", "D"} <= ids
    assert "E" not in ids


def test_traverse_beam_prunes(tmp_path: Path):
    graph = _build(tmp_path)
    # beam_width=1 keeps only the single best neighbor at each depth
    result = traverse(graph, [("A", 0.9)], max_depth=1, beam_width=1)
    ids = {c.node_id for c in result}
    # A is a seed; one of B or C is kept
    assert "A" in ids
    assert len(ids) == 2


def test_traverse_follows_backlinks(tmp_path: Path):
    """A->B should let starting from B reach A via backlink traversal."""
    graph = _build(tmp_path)
    result = traverse(graph, [("D", 0.9)], max_depth=1, beam_width=5)
    ids = {c.node_id for c in result}
    assert "D" in ids
    assert "B" in ids  # B links to D, so D can backlink to B


def test_traverse_skips_missing_targets(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "A.md").write_text("# A\nLinks to [[Missing]] only.", encoding="utf-8")
    graph = build_graph(parse_vault(vault))
    result = traverse(graph, [("A", 0.9)], max_depth=2, beam_width=5)
    ids = {c.node_id for c in result}
    assert ids == {"A"}


def test_traverse_no_seeds():
    import networkx as nx

    g = nx.DiGraph()
    assert traverse(g, [], max_depth=2) == []

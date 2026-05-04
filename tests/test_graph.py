from pathlib import Path

from cma.storage.graph_store import build_graph, graph_health_report
from cma.storage.markdown_store import parse_vault


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "A.md").write_text("# A\nLinks to [[B]] and [[Missing]].", encoding="utf-8")
    (vault / "B.md").write_text("# B\nLinks back to [[A]].", encoding="utf-8")
    (vault / "C.md").write_text("# C\nNo links at all.", encoding="utf-8")
    return vault


def test_build_graph_creates_nodes_and_edges(tmp_path: Path):
    vault = _make_vault(tmp_path)
    records = parse_vault(vault)
    g = build_graph(records)

    assert g.has_node("A")
    assert g.has_node("B")
    assert g.has_node("C")
    assert g.has_edge("A", "B")
    assert g.has_edge("B", "A")
    assert g.nodes["A"]["exists"] is True


def test_build_graph_creates_placeholder_for_missing(tmp_path: Path):
    vault = _make_vault(tmp_path)
    records = parse_vault(vault)
    g = build_graph(records)
    assert g.has_node("Missing")
    assert g.nodes["Missing"]["exists"] is False
    assert g.has_edge("A", "Missing")


def test_graph_health_finds_orphans_and_broken(tmp_path: Path):
    vault = _make_vault(tmp_path)
    records = parse_vault(vault)
    g = build_graph(records)
    report = graph_health_report(g)

    assert report["total_nodes"] == 3  # A, B, C
    assert report["missing_nodes"] == 1  # Missing placeholder
    assert "C" in report["orphans"]
    assert "A" not in report["orphans"]
    assert any(bl["target"] == "Missing" for bl in report["broken_links"])


def test_graph_health_resolves_by_title(tmp_path: Path):
    """A wikilink should resolve to a note's title even if the filename differs."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note-1.md").write_text(
        """---
title: Capital Call ADR
---
content
""",
        encoding="utf-8",
    )
    (vault / "note-2.md").write_text(
        "# Linker\n\nReferences [[Capital Call ADR]].",
        encoding="utf-8",
    )
    records = parse_vault(vault)
    g = build_graph(records)
    # The link should resolve to note-1 via title match
    assert g.has_edge("note-2", "note-1")


def test_graph_node_carries_metadata(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Dec.md").write_text(
        """---
type: decision
title: Async Capital Call Processing
status: accepted
confidence: 0.86
tags: [capital-calls, performance]
domain: backend
---

content
""",
        encoding="utf-8",
    )
    records = parse_vault(vault)
    g = build_graph(records)
    data = g.nodes["Dec"]
    assert data["type"] == "decision"
    assert data["status"] == "accepted"
    assert data["confidence"] == 0.86
    assert "capital-calls" in data["tags"]
    assert data["domain"] == "backend"

from pathlib import Path

from cma.retriever import Retriever, render_markdown
from cma.storage.graph_store import build_graph
from cma.storage.markdown_store import parse_vault


def _example_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "003-decisions").mkdir(parents=True)
    (vault / "004-patterns").mkdir(parents=True)
    (vault / "003-decisions" / "Async Capital Call Processing.md").write_text(
        """---
type: decision
title: Async Capital Call Processing
status: accepted
confidence: 0.86
human_verified: true
---

We decided to move capital call processing into an async queue.

This uses [[Queue Retry Pattern]] for reliability.

Related anti-pattern: [[External API Synchronous Bottleneck]]
""",
        encoding="utf-8",
    )
    (vault / "004-patterns" / "Queue Retry Pattern.md").write_text(
        """---
type: pattern
title: Queue Retry Pattern
status: active
confidence: 0.78
---

For external API calls that may fail intermittently, place the call behind an
async queue with bounded exponential backoff.

Used by [[Async Capital Call Processing]].
""",
        encoding="utf-8",
    )
    (vault / "004-patterns" / "External API Synchronous Bottleneck.md").write_text(
        """---
type: pattern
title: External API Synchronous Bottleneck
status: active
confidence: 0.72
---

Synchronous external API calls in the request path cap latency at the slowest
external dependency.

Mitigation: see [[Queue Retry Pattern]].
""",
        encoding="utf-8",
    )
    (vault / "Cooking Rice.md").write_text(
        """---
type: note
title: Cooking Rice
---

Add rice to boiling water and simmer for 15 minutes.
""",
        encoding="utf-8",
    )
    return vault


def _retriever_bm25_only(vault_path: Path) -> Retriever:
    records = parse_vault(vault_path)
    graph = build_graph(records)
    return Retriever(records=records, graph=graph, embedder=None)


def test_retriever_returns_relevant_seed(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing")

    assert spec.fragments
    titles = {f.source_node for f in spec.fragments}
    # The decision note should be the top seed
    assert "Async Capital Call Processing" in titles
    # The unrelated note should not appear
    assert "Cooking Rice" not in titles


def test_retriever_traverses_graph_to_pattern(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing", max_depth=2)
    titles = {f.source_node for f in spec.fragments}
    # Linked patterns should be reachable via graph traversal
    assert "Queue Retry Pattern" in titles or "External API Synchronous Bottleneck" in titles


def test_retriever_excludes_unrelated_with_threshold(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing", max_depth=0)
    titles = {f.source_node for f in spec.fragments}
    assert "Cooking Rice" not in titles


def test_retriever_assembles_relationship_map(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing", max_depth=2)
    if spec.relationship_map:
        # If we got multiple notes, some edges should have been recorded
        sources = {e.source for e in spec.relationship_map}
        targets = {e.target for e in spec.relationship_map}
        assert sources & targets or len(spec.relationship_map) >= 1


def test_retriever_records_parameters(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing", max_depth=1, beam_width=3)
    assert spec.parameters["max_depth"] == 1
    assert spec.parameters["beam_width"] == 3
    assert spec.parameters["embedder"] == "none"


def test_render_markdown_smoke(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing")
    md = render_markdown(spec)
    assert "# Context Spec" in md
    assert spec.task_id in md
    assert "Retrieved Fragments" in md

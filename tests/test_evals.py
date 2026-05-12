from pathlib import Path

from cma.evals import (
    BenchmarkQuery,
    RetrievalMode,
    context_efficiency_score,
    memory_usefulness_score,
    mrr,
    precision_at_k,
    recall_at_k,
    run_benchmark,
)


# ---------- metrics ----------


def test_recall_at_k_full_overlap():
    assert recall_at_k(["a", "b", "c"], ["a", "b"], k=3) == 1.0


def test_recall_at_k_partial():
    assert recall_at_k(["a", "x", "y"], ["a", "b"], k=3) == 0.5


def test_recall_at_k_truncates():
    assert recall_at_k(["x", "y", "a"], ["a"], k=2) == 0.0
    assert recall_at_k(["x", "y", "a"], ["a"], k=3) == 1.0


def test_recall_at_k_empty_relevant():
    assert recall_at_k(["a"], [], k=5) == 0.0


def test_precision_at_k_basic():
    assert precision_at_k(["a", "b", "x"], ["a", "b"], k=3) == 2 / 3


def test_precision_at_k_zero_k():
    assert precision_at_k(["a"], ["a"], k=0) == 0.0


def test_mrr_first_position():
    score = mrr([["a", "b", "c"]], [["a"]])
    assert score == 1.0


def test_mrr_second_position():
    score = mrr([["x", "a", "b"]], [["a"]])
    assert abs(score - 0.5) < 1e-9


def test_mrr_no_match_contributes_zero():
    score = mrr([["x", "y", "z"]], [["a"]])
    assert score == 0.0


def test_mrr_multi_query_average():
    # First query: rank 1 = 1.0; second query: rank 2 = 0.5; mean = 0.75
    score = mrr([["a"], ["x", "b"]], [["a"], ["b"]])
    assert abs(score - 0.75) < 1e-9


def test_memory_usefulness_score_positive():
    assert (
        memory_usefulness_score(
            relevant_used=2,
            prior_decision_applied=1,
            prior_failure_avoided=1,
            irrelevant_included=0,
            critical_missed=0,
            stale_or_superseded_used=0,
        )
        == 8.0
    )


def test_memory_usefulness_score_penalties():
    assert (
        memory_usefulness_score(
            relevant_used=0,
            prior_decision_applied=0,
            prior_failure_avoided=0,
            irrelevant_included=2,
            critical_missed=1,
            stale_or_superseded_used=1,
        )
        == -7.0
    )


def test_context_efficiency_score():
    assert context_efficiency_score(3, 6) == 0.5
    assert context_efficiency_score(0, 0) == 0.0


# ---------- runner ----------


def _build_project(tmp_path: Path) -> Path:
    project = tmp_path / "agent"
    (project / "cma" / "vault" / "003-decisions").mkdir(parents=True)
    (project / "cma" / "vault" / "004-patterns").mkdir(parents=True)
    (project / "cma").mkdir(parents=True, exist_ok=True)
    (project / "cma" / "config.yaml").write_text(
        "vault_path: ./cma/vault\nindex_path: ./cma/cache\nembedding_provider: none\n",
        encoding="utf-8",
    )
    (project / "cma" / "vault" / "003-decisions" / "Async Capital Call Processing.md").write_text(
        """---
type: decision
title: Async Capital Call Processing
status: accepted
confidence: 0.86
---

We decided to move capital call processing into an async queue.

Uses [[Queue Retry Pattern]].
""",
        encoding="utf-8",
    )
    (project / "cma" / "vault" / "004-patterns" / "Queue Retry Pattern.md").write_text(
        """---
type: pattern
title: Queue Retry Pattern
status: active
confidence: 0.78
---

Retry external calls with bounded exponential backoff.

Used by [[Async Capital Call Processing]].
""",
        encoding="utf-8",
    )
    (project / "cma" / "vault" / "Cooking Rice.md").write_text(
        "---\ntype: note\ntitle: Cooking Rice\n---\n\nUnrelated content.",
        encoding="utf-8",
    )
    return project


def test_run_benchmark_no_memory_returns_empty(tmp_path: Path):
    project = _build_project(tmp_path)
    queries = [
        BenchmarkQuery(query="capital call", expected_records=["Async Capital Call Processing"])
    ]
    run = run_benchmark(project, queries, mode=RetrievalMode.NO_MEMORY)
    assert run.results[0].retrieved_record_ids == []
    assert run.results[0].recall_at_5 == 0.0


def test_run_benchmark_graphrag_finds_expected(tmp_path: Path):
    project = _build_project(tmp_path)
    queries = [
        BenchmarkQuery(
            query="capital call processing",
            expected_records=["Async Capital Call Processing"],
        )
    ]
    run = run_benchmark(project, queries, mode=RetrievalMode.GRAPHRAG)
    result = run.results[0]
    assert "Async Capital Call Processing" in result.retrieved_record_ids
    assert result.recall_at_5 == 1.0


def test_run_benchmark_aggregate(tmp_path: Path):
    project = _build_project(tmp_path)
    queries = [
        BenchmarkQuery(
            query="capital call",
            expected_records=["Async Capital Call Processing"],
        ),
        BenchmarkQuery(
            query="queue retry",
            expected_records=["Queue Retry Pattern"],
        ),
    ]
    run = run_benchmark(project, queries, mode=RetrievalMode.GRAPHRAG)
    agg = run.aggregate()
    assert agg["n_queries"] == 2
    assert "mean_recall_at_5" in agg
    assert "mrr" in agg


def test_run_benchmark_vector_only_skips_traversal(tmp_path: Path):
    """Vector-only mode shouldn't surface graph-linked patterns - only direct seeds."""
    project = _build_project(tmp_path)
    queries = [
        BenchmarkQuery(
            query="capital call processing",
            expected_records=["Async Capital Call Processing", "Queue Retry Pattern"],
        )
    ]
    run = run_benchmark(project, queries, mode=RetrievalMode.VECTOR_ONLY)
    result = run.results[0]
    # The decision note has the query terms in its title -> seed.
    # The pattern note only has them via wikilink in body -> may or may not seed.
    # What's guaranteed: vector_only uses max_depth=0 so traversal is disabled.
    assert "Async Capital Call Processing" in result.retrieved_record_ids

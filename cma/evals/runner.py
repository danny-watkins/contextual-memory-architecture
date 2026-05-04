"""Benchmark runner: run a list of queries through CMA in a chosen mode and
score the retrieval against ground-truth relevance labels.

This is the Phase 7 skeleton. It currently supports retrieval-quality eval
(Levels 1 and 2 from whitepaper section 14.1). Full agent-improvement eval
(Level 3) requires running an actual LLM-based agent and is left for the
caller to wire together using these primitives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from cma.evals.metrics import (
    context_efficiency_score,
    memory_usefulness_score,
    mrr,
    precision_at_k,
    recall_at_k,
)
from cma.retriever import Retriever


class RetrievalMode(str, Enum):
    """Whitepaper section 14.2: the four comparison modes."""

    NO_MEMORY = "no_memory"      # Mode A: nothing retrieved
    VECTOR_ONLY = "vector_only"  # Mode B: BM25-only seeds, no graph traversal
    GRAPHRAG = "graphrag"        # Mode C: full Retriever, fixed vault
    FULL_CMA = "full_cma"        # Mode D: Mode C + Recorder writes between tasks


class BenchmarkQuery(BaseModel):
    """A single query plus its expected relevant notes.

    `expected_records` should hold the record_ids (filename stems) of notes
    that an ideal Retriever would surface. `tags` are optional labels for
    filtering the benchmark suite (e.g. by query type: local / multi-hop / global).
    """

    query: str
    expected_records: list[str] = Field(default_factory=list)
    expected_paragraphs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


@dataclass
class BenchmarkResult:
    query: str
    retrieved_record_ids: list[str]
    expected_record_ids: list[str]
    recall_at_5: float
    precision_at_5: float
    n_fragments: int
    n_unique_sources: int
    raw_spec_token_estimate: int


@dataclass
class BenchmarkRun:
    mode: RetrievalMode
    project_path: Path
    started_at: datetime
    results: list[BenchmarkResult] = field(default_factory=list)

    def aggregate(self) -> dict[str, float]:
        if not self.results:
            return {}
        n = len(self.results)
        retrieved_lists = [r.retrieved_record_ids for r in self.results]
        relevant_lists = [r.expected_record_ids for r in self.results]
        return {
            "n_queries": n,
            "mean_recall_at_5": sum(r.recall_at_5 for r in self.results) / n,
            "mean_precision_at_5": sum(r.precision_at_5 for r in self.results) / n,
            "mrr": mrr(retrieved_lists, relevant_lists),
            "mean_fragments": sum(r.n_fragments for r in self.results) / n,
            "mean_unique_sources": sum(r.n_unique_sources for r in self.results) / n,
            "mean_token_estimate": sum(r.raw_spec_token_estimate for r in self.results) / n,
        }


def _estimate_tokens(text_segments: list[str]) -> int:
    """Rough token estimate: 1 token per 4 characters."""
    return sum(len(s) for s in text_segments) // 4


def load_benchmark_queries(path: Path) -> list[BenchmarkQuery]:
    """Load a YAML or JSON benchmark suite into BenchmarkQuery objects."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict) and "queries" in data:
        data = data["queries"]
    return [BenchmarkQuery(**q) for q in data]


def run_benchmark(
    project_path: Path,
    queries: list[BenchmarkQuery],
    mode: RetrievalMode = RetrievalMode.GRAPHRAG,
    max_depth: int | None = None,
    beam_width: int | None = None,
) -> BenchmarkRun:
    """Run a benchmark suite against a CMA project in the given mode.

    Mode A (NO_MEMORY) returns empty retrievals - useful as a control.
    Mode B (VECTOR_ONLY) runs hybrid search but disables graph traversal.
    Mode C (GRAPHRAG) is the default Retriever.
    Mode D (FULL_CMA) is the same as C for one-shot eval; longitudinal eval
    requires multiple runs with Recorder writes between, which is the caller's
    responsibility.
    """
    project_path = Path(project_path).resolve()
    run = BenchmarkRun(
        mode=mode,
        project_path=project_path,
        started_at=datetime.now(timezone.utc),
    )

    if mode == RetrievalMode.NO_MEMORY:
        for q in queries:
            run.results.append(
                BenchmarkResult(
                    query=q.query,
                    retrieved_record_ids=[],
                    expected_record_ids=q.expected_records,
                    recall_at_5=recall_at_k([], q.expected_records, 5),
                    precision_at_5=precision_at_k([], q.expected_records, 5),
                    n_fragments=0,
                    n_unique_sources=0,
                    raw_spec_token_estimate=0,
                )
            )
        return run

    retriever = Retriever.from_project(project_path)
    effective_depth = (
        0
        if mode == RetrievalMode.VECTOR_ONLY
        else (max_depth if max_depth is not None else retriever.config.max_depth)
    )

    title_to_id: dict[str, str] = {
        rec.title.lower(): rec.record_id for rec in retriever.records
    }

    for q in queries:
        spec = retriever.retrieve(
            q.query,
            max_depth=effective_depth,
            beam_width=beam_width if beam_width is not None else retriever.config.beam_width,
        )
        # Map fragment source titles back to record_ids for scoring.
        retrieved_ids: list[str] = []
        seen: set[str] = set()
        for frag in spec.fragments:
            rid = title_to_id.get(frag.source_node.lower(), frag.source_node)
            if rid not in seen:
                seen.add(rid)
                retrieved_ids.append(rid)

        run.results.append(
            BenchmarkResult(
                query=q.query,
                retrieved_record_ids=retrieved_ids,
                expected_record_ids=q.expected_records,
                recall_at_5=recall_at_k(retrieved_ids, q.expected_records, 5),
                precision_at_5=precision_at_k(retrieved_ids, q.expected_records, 5),
                n_fragments=len(spec.fragments),
                n_unique_sources=len(seen),
                raw_spec_token_estimate=_estimate_tokens([f.text for f in spec.fragments]),
            )
        )

    return run


__all__ = [
    "BenchmarkQuery",
    "BenchmarkResult",
    "BenchmarkRun",
    "RetrievalMode",
    "load_benchmark_queries",
    "run_benchmark",
    "memory_usefulness_score",
    "context_efficiency_score",
]

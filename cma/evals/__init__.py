"""Evaluation harness - measure whether CMA is getting smarter over time.

Implements the four-mode comparison from the whitepaper:
  Mode A: no memory       (baseline)
  Mode B: vector-only     (BM25 lexical only, no embeddings, no graph)
  Mode C: GraphRAG fixed  (full retrieval over a fixed vault)
  Mode D: full CMA        (Mode C + Recorder writing back between tasks)

Plus the metrics: Recall@k, Precision@k, MRR, Memory Usefulness Score,
Context Efficiency Score.
"""

from cma.evals.metrics import (
    context_efficiency_score,
    memory_usefulness_score,
    mrr,
    precision_at_k,
    recall_at_k,
)
from cma.evals.runner import (
    BenchmarkQuery,
    BenchmarkResult,
    RetrievalMode,
    run_benchmark,
)

__all__ = [
    "recall_at_k",
    "precision_at_k",
    "mrr",
    "memory_usefulness_score",
    "context_efficiency_score",
    "BenchmarkQuery",
    "BenchmarkResult",
    "RetrievalMode",
    "run_benchmark",
]

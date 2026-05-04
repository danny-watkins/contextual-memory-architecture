"""Memory health and observability.

Answers "how big is my agent's memory and is it healthy?":
  - vault size by folder
  - derived index sizes (graph, BM25, embeddings)
  - graph density (orphan rate, broken link rate, average degree)
  - retrieval activity (which notes get pulled, which never have)
  - soft-threshold warnings ("vault > 50K notes, consider archival")

Surface: `cma health` CLI command and `health_report()` Python API.
"""

from cma.health.report import (
    THRESHOLDS,
    health_report,
    log_retrieval,
    read_retrieval_log,
)

__all__ = ["THRESHOLDS", "health_report", "log_retrieval", "read_retrieval_log"]

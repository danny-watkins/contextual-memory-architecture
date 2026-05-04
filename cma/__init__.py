"""Contextual Memory Architecture (CMA) - a local-first memory layer for AI agents."""

__version__ = "0.2.0"

from cma.config import CMAConfig, RecorderConfig, RetrievalConfig
from cma.recorder import Recorder, RecorderResult, WriteDecision
from cma.retriever import (
    BM25Index,
    Embedder,
    EmbedderUnavailable,
    OpenAIEmbedder,
    Retriever,
    SentenceTransformerEmbedder,
    get_embedder,
    render_markdown,
)
from cma.schemas import (
    CompletionPackage,
    ContextRequest,
    ContextSpec,
    ContextUsage,
    Decision,
    Exclusion,
    Fragment,
    MemoryRecord,
    Pattern,
    RelationshipEdge,
    TaskFrame,
)
from cma.storage.graph_store import build_graph, graph_health_report
from cma.storage.markdown_store import (
    extract_wikilinks,
    parse_note,
    parse_vault,
    walk_vault,
)

__all__ = [
    "__version__",
    "CMAConfig",
    "RetrievalConfig",
    "RecorderConfig",
    "TaskFrame",
    "ContextRequest",
    "ContextSpec",
    "Fragment",
    "RelationshipEdge",
    "Exclusion",
    "CompletionPackage",
    "Decision",
    "Pattern",
    "ContextUsage",
    "MemoryRecord",
    "parse_note",
    "parse_vault",
    "walk_vault",
    "extract_wikilinks",
    "build_graph",
    "graph_health_report",
    "Recorder",
    "RecorderResult",
    "WriteDecision",
    "Retriever",
    "Embedder",
    "EmbedderUnavailable",
    "SentenceTransformerEmbedder",
    "OpenAIEmbedder",
    "BM25Index",
    "get_embedder",
    "render_markdown",
]

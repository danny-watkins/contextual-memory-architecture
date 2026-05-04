"""Retriever - hybrid search + graph traversal + context spec assembly."""

from cma.retriever.embeddings import (
    Embedder,
    EmbedderUnavailable,
    EmbeddingIndex,
    OpenAIEmbedder,
    SentenceTransformerEmbedder,
    get_embedder,
)
from cma.retriever.fragments import (
    deduplicate_fragments,
    select_fragments,
    split_paragraphs,
)
from cma.retriever.lexical import BM25Index, tokenize
from cma.retriever.retriever import Retriever
from cma.retriever.scoring import (
    apply_depth_decay,
    final_score,
    hybrid_node_score,
    metadata_boost,
)
from cma.retriever.spec_builder import build_context_spec, render_markdown
from cma.retriever.traversal import Candidate, traverse

__all__ = [
    "Retriever",
    "Embedder",
    "EmbedderUnavailable",
    "EmbeddingIndex",
    "SentenceTransformerEmbedder",
    "OpenAIEmbedder",
    "get_embedder",
    "BM25Index",
    "tokenize",
    "split_paragraphs",
    "select_fragments",
    "deduplicate_fragments",
    "hybrid_node_score",
    "metadata_boost",
    "apply_depth_decay",
    "final_score",
    "Candidate",
    "traverse",
    "build_context_spec",
    "render_markdown",
]

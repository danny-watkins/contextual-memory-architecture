"""Pluggable embedder protocol and built-in implementations.

The default embedder is sentence-transformers (local, no API key). OpenAI is
available as an extra. Users can also implement their own embedder by
matching the Embedder protocol and passing it to Retriever directly.

Both built-in embedders are imported lazily so the package installs and runs
without their heavy dependencies.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Embedder(Protocol):
    """Anything that can turn texts into a (n, dim) numpy array of vectors."""

    @property
    def name(self) -> str: ...

    @property
    def dim(self) -> int: ...

    def embed(self, texts: list[str]) -> np.ndarray: ...


class EmbedderUnavailable(RuntimeError):
    """Raised when an embedder is requested but its dependency isn't installed."""


class SentenceTransformerEmbedder:
    """Local embeddings via sentence-transformers. Default model: all-MiniLM-L6-v2."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise EmbedderUnavailable(
                "sentence-transformers is not installed. "
                "Install with: pip install 'contextual-memory-architecture[embeddings]'"
            ) from e
        self._model = SentenceTransformer(model_name)
        self._name = model_name

    @property
    def name(self) -> str:
        return f"sentence-transformers:{self._name}"

    @property
    def dim(self) -> int:
        return int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vecs, dtype=np.float32)


class OpenAIEmbedder:
    """OpenAI embeddings. Requires OPENAI_API_KEY in env or passed explicitly."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise EmbedderUnavailable(
                "openai is not installed. "
                "Install with: pip install 'contextual-memory-architecture[openai]'"
            ) from e
        self._client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self._model = model
        self._dim_cache: int | None = None

    @property
    def name(self) -> str:
        return f"openai:{self._model}"

    @property
    def dim(self) -> int:
        if self._dim_cache is None:
            self._dim_cache = int(self.embed(["dim probe"]).shape[1])
        return self._dim_cache

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            # Can't know dim without a probe; assume already cached or default to 1536.
            return np.zeros((0, self._dim_cache or 1536), dtype=np.float32)
        resp = self._client.embeddings.create(input=texts, model=self._model)
        arr = np.array([d.embedding for d in resp.data], dtype=np.float32)
        # L2-normalize so dot product equals cosine similarity.
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms


def get_embedder(provider: str, model: str) -> Embedder | None:
    """Resolve a (provider, model) pair to an Embedder, or None if disabled.

    Provider values:
      - "none"                        -> None (BM25-only retrieval)
      - "sentence-transformers"       -> SentenceTransformerEmbedder
      - "openai"                      -> OpenAIEmbedder

    Raises EmbedderUnavailable if the requested provider's package is missing.
    """
    if provider in ("none", "", None):
        return None
    if provider == "sentence-transformers":
        return SentenceTransformerEmbedder(model)
    if provider == "openai":
        return OpenAIEmbedder(model)
    raise ValueError(f"Unknown embedding provider: {provider}")


class EmbeddingIndex:
    """A flat numpy matrix of normalized embeddings keyed by record_id.

    For now this is in-memory only; the index command writes the matrix and
    doc_ids to .cma/embeddings/ for warm starts.
    """

    def __init__(self, doc_ids: list[str], matrix: np.ndarray, embedder_name: str):
        if matrix.shape[0] != len(doc_ids):
            raise ValueError("doc_ids and matrix row count must match")
        self.doc_ids = doc_ids
        self.matrix = matrix.astype(np.float32, copy=False)
        self.embedder_name = embedder_name

    @classmethod
    def build(cls, records, embedder: Embedder) -> "EmbeddingIndex":
        doc_ids = [r.record_id for r in records]
        texts = [(r.title + "\n\n" + r.body) for r in records]
        matrix = embedder.embed(texts) if texts else np.zeros((0, embedder.dim), dtype=np.float32)
        return cls(doc_ids, matrix, embedder.name)

    def search(
        self, query_vec: np.ndarray, top_k: int = 10
    ) -> list[tuple[str, float]]:
        if self.matrix.shape[0] == 0:
            return []
        # query_vec assumed normalized; matrix rows assumed normalized.
        scores = self.matrix @ query_vec.reshape(-1)
        # Clip to [0, 1] - cosine of normalized vectors is in [-1, 1] but for
        # text embeddings near-zero or negative scores aren't useful here.
        scores = np.clip(scores, 0.0, 1.0)
        order = np.argsort(-scores)[:top_k]
        return [(self.doc_ids[i], float(scores[i])) for i in order if scores[i] > 0]

"""Top-level Retriever: turn a query into a ContextSpec.

Pipeline:
    1. Hybrid seed search (BM25 + optional embeddings)
    2. Beam-pruned graph traversal
    3. Score every candidate (hybrid + metadata boost + depth decay)
    4. Threshold-prune low-scoring nodes
    5. Extract paragraph-level fragments per node
    6. Deduplicate fragments across nodes
    7. Assemble the ContextSpec
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from cma import __version__
from cma.config import CMAConfig, RetrievalConfig
from cma.retriever.embeddings import (
    Embedder,
    EmbedderUnavailable,
    EmbeddingIndex,
    get_embedder,
)
from cma.retriever.fragments import deduplicate_fragments, select_fragments
from cma.retriever.lexical import BM25Index
from cma.retriever.scoring import final_score, hybrid_node_score, metadata_boost
from cma.retriever.spec_builder import build_context_spec
from cma.retriever.traversal import traverse
from cma.schemas.context_spec import ContextSpec, Fragment, RelationshipEdge
from cma.schemas.memory_record import MemoryRecord
from cma.storage.graph_store import build_graph
from cma.storage.markdown_store import parse_vault


class Retriever:
    """Stateful retriever that holds parsed records, graph, BM25, and (optional) embeddings."""

    def __init__(
        self,
        records: list[MemoryRecord],
        graph,
        config: RetrievalConfig | None = None,
        embedder: Embedder | None = None,
        project_path: Path | None = None,
    ) -> None:
        self.records = records
        self.records_by_id: dict[str, MemoryRecord] = {r.record_id: r for r in records}
        self.graph = graph
        self.config = config or RetrievalConfig()
        self.embedder = embedder
        self.project_path = Path(project_path).resolve() if project_path else None
        self.bm25 = BM25Index(records)
        self.embedding_index: EmbeddingIndex | None = (
            EmbeddingIndex.build(records, embedder) if embedder else None
        )

    @classmethod
    def from_project(
        cls,
        project_path: Path,
        embedder: Embedder | None | str = "auto",
    ) -> "Retriever":
        """Build a Retriever from a CMA project on disk.

        embedder='auto' tries to construct the configured embedder and falls
        back to BM25-only if its dependency isn't installed. Pass None to skip
        embeddings explicitly, or pass an Embedder instance to inject your own.
        """
        config = CMAConfig.from_project(project_path).resolve_paths(project_path)
        records = parse_vault(Path(config.vault_path))
        graph = build_graph(records)

        resolved: Embedder | None
        if embedder == "auto":
            try:
                resolved = get_embedder(config.embedding_provider, config.embedding_model)
            except EmbedderUnavailable:
                resolved = None
        elif isinstance(embedder, str):
            resolved = None
        else:
            resolved = embedder

        return cls(
            records=records,
            graph=graph,
            config=config.retrieval,
            embedder=resolved,
            project_path=Path(project_path).resolve(),
        )

    # ----- internals -----

    def _seed_scores(self, query: str, top_k: int) -> dict[str, tuple[float, float]]:
        """Return record_id -> (semantic_score, lexical_score) for the union of top results."""
        lexical = dict(self.bm25.search(query, top_k=top_k))

        semantic: dict[str, float] = {}
        if self.embedding_index is not None and self.embedder is not None:
            qvec = self.embedder.embed([query])
            if qvec.shape[0] > 0:
                # Ensure normalized for cosine via dot.
                norm = np.linalg.norm(qvec[0])
                if norm > 0:
                    qvec = qvec / norm
                semantic = dict(self.embedding_index.search(qvec[0], top_k=top_k))

        out: dict[str, tuple[float, float]] = {}
        for rid in set(lexical) | set(semantic):
            out[rid] = (semantic.get(rid, 0.0), lexical.get(rid, 0.0))
        return out

    def _select_seeds(
        self, query: str, top_k: int, alpha: float, node_threshold: float
    ) -> list[tuple[str, float]]:
        """Pick the strongest hybrid-search hits as seeds.

        Only docs scoring at or above node_threshold qualify as seeds. Weaker
        hits can still be surfaced later via graph traversal from a strong seed.
        """
        scored = self._seed_scores(query, top_k=top_k)
        ranked: list[tuple[str, float]] = []
        for rid, (sem, lex) in scored.items():
            score = hybrid_node_score(sem, lex, alpha)
            if score >= node_threshold:
                ranked.append((rid, score))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def _score_candidates(
        self,
        query: str,
        candidates: list,
        alpha: float,
        depth_decay: float,
    ) -> list[tuple[MemoryRecord, int, float]]:
        # Re-score every candidate against the query, including hop-2 nodes
        # that didn't make the seed cut.
        results: list[tuple[MemoryRecord, int, float]] = []
        bm25_scores = dict(self.bm25.search(query, top_k=len(self.records) or 1))

        sem_scores: dict[str, float] = {}
        if self.embedding_index is not None and self.embedder is not None:
            qvec = self.embedder.embed([query])
            if qvec.shape[0] > 0:
                norm = np.linalg.norm(qvec[0])
                if norm > 0:
                    qvec = qvec / norm
                sem_scores = dict(
                    self.embedding_index.search(qvec[0], top_k=len(self.records) or 1)
                )

        for cand in candidates:
            rec = self.records_by_id.get(cand.node_id)
            if rec is None:
                continue
            sem = sem_scores.get(cand.node_id, 0.0)
            lex = bm25_scores.get(cand.node_id, 0.0)
            score = final_score(sem, lex, rec, cand.depth, alpha=alpha, depth_decay=depth_decay)
            results.append((rec, cand.depth, score))
        return results

    def _extract_node_fragments(
        self,
        scored: list[tuple[MemoryRecord, int, float]],
        query: str,
        fragment_threshold: float,
        max_fragments_per_node: int,
    ) -> list[Fragment]:
        """Extract paragraph fragments from every candidate.

        node_threshold is not applied here - seeds were already filtered by it
        in _select_seeds, and traversed nodes earn their place by graph
        adjacency, not by direct query match.
        """
        all_frags: list[tuple[str, str, float, MemoryRecord, int, float]] = []
        for rec, depth, node_score in scored:
            picks = select_fragments(
                rec.body, query, max_fragments=max_fragments_per_node, min_score=0.0
            )
            for text, frag_score in picks:
                all_frags.append((rec.record_id, text, frag_score, rec, depth, node_score))

        # Deduplicate across nodes
        plain = [(src, text, score) for src, text, score, _, _, _ in all_frags]
        deduped = {(src, text) for src, text, _ in deduplicate_fragments(plain)}

        fragments: list[Fragment] = []
        for rec_id, text, frag_score, rec, depth, node_score in all_frags:
            if (rec_id, text) not in deduped:
                continue
            if frag_score < fragment_threshold and depth > 0:
                # Allow fragments from seed nodes through even if they score low
                # against the query (they often contain context the query implies).
                continue
            fragments.append(
                Fragment(
                    source_node=rec.title,
                    node_type=rec.type,
                    node_score=round(node_score, 4),
                    fragment_score=round(frag_score, 4),
                    depth=depth,
                    text=text,
                    why_included=_why_included(rec, depth, node_score),
                )
            )
        # Sort: depth asc (seeds first), then node_score desc, then fragment_score desc
        fragments.sort(key=lambda f: (f.depth, -f.node_score, -f.fragment_score))
        return fragments

    def _relationship_map(
        self, scored: list[tuple[MemoryRecord, int, float]]
    ) -> list[RelationshipEdge]:
        included_ids = {rec.record_id for rec, _, _ in scored}
        edges: list[RelationshipEdge] = []
        for src in included_ids:
            for tgt in self.graph.successors(src):
                if tgt in included_ids:
                    edges.append(RelationshipEdge(source=src, target=tgt))
        return edges

    # ----- public API -----

    def retrieve(
        self,
        query: str,
        *,
        task_id: str | None = None,
        max_depth: int | None = None,
        beam_width: int | None = None,
        alpha: float | None = None,
        node_threshold: float | None = None,
        fragment_threshold: float | None = None,
        depth_decay: float | None = None,
        max_fragments_per_node: int | None = None,
        seed_top_k: int = 10,
    ) -> ContextSpec:
        cfg = self.config
        max_depth = max_depth if max_depth is not None else cfg.max_depth
        beam_width = beam_width if beam_width is not None else cfg.beam_width
        alpha = alpha if alpha is not None else cfg.alpha
        node_threshold = node_threshold if node_threshold is not None else cfg.node_threshold
        fragment_threshold = (
            fragment_threshold if fragment_threshold is not None else cfg.fragment_threshold
        )
        depth_decay = depth_decay if depth_decay is not None else cfg.depth_decay
        max_fragments_per_node = (
            max_fragments_per_node
            if max_fragments_per_node is not None
            else cfg.max_fragments_per_node
        )

        seeds = self._select_seeds(
            query, top_k=seed_top_k, alpha=alpha, node_threshold=node_threshold
        )
        candidates = traverse(self.graph, seeds, max_depth=max_depth, beam_width=beam_width)
        scored = self._score_candidates(query, candidates, alpha=alpha, depth_decay=depth_decay)
        fragments = self._extract_node_fragments(
            scored,
            query,
            fragment_threshold=fragment_threshold,
            max_fragments_per_node=max_fragments_per_node,
        )
        relationship_map = self._relationship_map(scored)

        params = {
            "max_depth": max_depth,
            "beam_width": beam_width,
            "alpha": alpha,
            "node_threshold": node_threshold,
            "fragment_threshold": fragment_threshold,
            "depth_decay": depth_decay,
            "max_fragments_per_node": max_fragments_per_node,
            "embedder": self.embedder.name if self.embedder else "none",
        }
        spec = build_context_spec(
            task_id=task_id or "ad-hoc",
            query=query,
            parameters=params,
            fragments=fragments,
            relationship_map=relationship_map,
            retriever_version=__version__,
        )
        if self.project_path is not None:
            try:
                from cma.health.report import log_retrieval

                token_est = sum(len(f.text) for f in spec.fragments) // 4
                log_retrieval(
                    self.project_path,
                    spec_id=spec.spec_id,
                    task_id=spec.task_id,
                    query=query,
                    fragment_titles=list({f.source_node for f in spec.fragments}),
                    token_estimate=token_est,
                    fragment_count=len(spec.fragments),
                )
            except Exception:
                # Logging is best-effort; never break a retrieve because the log dir is bad.
                pass
        return spec


def _why_included(record: MemoryRecord, depth: int, score: float) -> str:
    """Generate a short explanation for why a node is in the context spec."""
    parts: list[str] = []
    if depth == 0:
        parts.append("seed match")
    else:
        parts.append(f"reached at depth {depth}")
    if record.type != "note":
        parts.append(f"type={record.type}")
    if record.status not in ("active", "draft"):
        parts.append(f"status={record.status}")
    parts.append(f"score={score:.2f}")
    return ", ".join(parts)

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
import time
from datetime import datetime, timezone

from cma.retriever.fragments import deduplicate_fragments, select_fragments
from cma.retriever.lexical import BM25Index
from cma.retriever.scoring import (
    final_score,
    hybrid_node_score,
    metadata_boost,
    title_match_boost,
)
from cma.retriever.spec_builder import (
    build_context_spec,
    new_spec_id,
    write_spec_stub,
    write_spec_to_vault,
)
from cma.retriever.traversal import traverse
from cma.schemas.context_spec import ContextSpec, Fragment, RelationshipEdge
from cma.schemas.memory_record import MemoryRecord
from cma.storage.graph_store import build_graph
from cma.storage.markdown_store import parse_vault, update_frontmatter


class Retriever:
    """Stateful retriever that holds parsed records, graph, BM25, and (optional) embeddings."""

    def __init__(
        self,
        records: list[MemoryRecord],
        graph,
        config: RetrievalConfig | None = None,
        embedder: Embedder | None = None,
        project_path: Path | None = None,
        vault_path: Path | None = None,
    ) -> None:
        self.records = records
        self.records_by_id: dict[str, MemoryRecord] = {r.record_id: r for r in records}
        self.graph = graph
        self.config = config or RetrievalConfig()
        self.embedder = embedder
        self.project_path = Path(project_path).resolve() if project_path else None
        self.vault_path = Path(vault_path).resolve() if vault_path else None
        # Records eligible for seed ranking. Two classes of note are excluded
        # from the search index entirely (not just at threshold time) because
        # they store the user's literal query in their body and would otherwise
        # dominate BM25 normalization — squashing legitimate hits to near-zero:
        #   - `type: context_spec` — derived artifacts written by prior
        #     retrieves (GraphRAG flywheel poisoning).
        #   - `status: noise` — inbox-captured prompts (whitepaper §5.8).
        # Both remain in self.records so the graph can still treat them as
        # nodes (e.g. for traversal from a curated seed that wikilinks to one).
        seedable = [
            r for r in records
            if r.type != "context_spec" and r.status != "noise"
        ]
        self.bm25 = BM25Index(seedable)
        self.embedding_index: EmbeddingIndex | None = (
            EmbeddingIndex.build(seedable, embedder) if embedder else None
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
            vault_path=Path(config.vault_path).resolve(),
        )

    # ----- internals -----

    def _seed_scores(self, query: str, top_k: int) -> dict[str, tuple[float, float]]:
        """Return record_id -> (semantic_score, lexical_score) for the union of top results.

        Fetches a wider raw pool than `top_k` (5× or 50, whichever is larger)
        so that boost/title-match re-ranking inside `_select_seeds` has room
        to elevate buried-but-relevant records. Without this, a memory-tier
        note that sits at raw BM25 rank ~20 (because substrate JSON files
        dominate lexical density) would never reach the re-rank stage.
        """
        pool_k = max(top_k * 5, 50)
        lexical = dict(self.bm25.search(query, top_k=pool_k))

        semantic: dict[str, float] = {}
        if self.embedding_index is not None and self.embedder is not None:
            qvec = self.embedder.embed([query])
            if qvec.shape[0] > 0:
                # Ensure normalized for cosine via dot.
                norm = np.linalg.norm(qvec[0])
                if norm > 0:
                    qvec = qvec / norm
                semantic = dict(self.embedding_index.search(qvec[0], top_k=pool_k))

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

        Three pre-filters before scoring:

        * `type == "context_spec"`: derived artifacts written by prior retrieves;
          they store the user's query verbatim and would perfectly self-match
          on substring queries (GraphRAG-flywheel poisoning). They remain in
          the corpus for graph traversal but never seed.
        * `status == "noise"`: inbox-captured prompts (whitepaper §5.8). Same
          self-match problem — they contain the literal query.
        * Anything else then goes through the full metadata-boosted score, so
          substrate-tier source files and raw code/config don't outrank curated
          memory notes purely on lexical density.
        """
        scored = self._seed_scores(query, top_k=top_k)
        ranked: list[tuple[str, float]] = []
        for rid, (sem, lex) in scored.items():
            rec = self.records_by_id.get(rid)
            if rec is None:
                continue
            if rec.type == "context_spec":
                continue
            if rec.status == "noise":
                continue
            hybrid = hybrid_node_score(sem, lex, alpha)
            boosted = hybrid * metadata_boost(rec) * title_match_boost(rec, query)
            if boosted >= node_threshold:
                ranked.append((rid, boosted))
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
            # Mirror the seed-time filter for traversed nodes: context_spec and
            # noise prompts may be reached via wikilinks from a real seed, but
            # they should never appear in the user-visible result set — they
            # are derived/inbox artifacts, not source content.
            if rec.type == "context_spec" or rec.status == "noise":
                continue
            sem = sem_scores.get(cand.node_id, 0.0)
            lex = bm25_scores.get(cand.node_id, 0.0)
            score = final_score(sem, lex, rec, cand.depth, alpha=alpha, depth_decay=depth_decay)
            # Title-match super-boost: applied here too so traversed nodes whose
            # titles match the query also surface above generic neighbors.
            score *= title_match_boost(rec, query)
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
        demo: bool = False,
        demo_step_seconds: float = 0.8,
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

        spec_id = new_spec_id()
        if demo and self.vault_path:
            self._demo_walk(
                spec_id=spec_id,
                task_id=task_id or "ad-hoc",
                query=query,
                candidates=candidates,
                step_seconds=demo_step_seconds,
            )

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
            spec_id=spec_id,
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

        if self.vault_path is not None:
            if not demo:
                # In demo mode, _demo_walk already touched each node as the
                # cursor visited it. Don't double-bump retrieve_count here.
                self._touch_visited_notes(spec)
            self._persist_spec_note(spec)
        return spec

    # ----- side effects: live graph visualization -----

    def _demo_walk(
        self,
        *,
        spec_id: str,
        task_id: str,
        query: str,
        candidates: list,
        step_seconds: float,
    ) -> None:
        """Walk a visible cursor through `candidates` one node at a time.

        For each candidate:
            1. Demote previous (clear cma_active, set last_retrieved_at, +1 count)
            2. Set cma_active=true on the current node
            3. Append this source to the in-progress spec stub
            4. Sleep step_seconds so Obsidian re-renders between hops

        Final demotion happens at the end so no node is left with cma_active=true.
        Best-effort throughout: a single failed write must not abort the walk.
        """
        if not self.vault_path:
            return
        try:
            write_spec_stub(
                self.vault_path,
                spec_id=spec_id,
                task_id=task_id,
                query=query,
                sources_so_far=[],
                retriever_version=__version__,
            )
        except Exception:
            return

        sources_so_far: list[str] = []
        seen_ids: set[str] = set()
        prev_id: str | None = None

        for cand in candidates:
            rec = self.records_by_id.get(cand.node_id)
            if rec is None or rec.record_id in seen_ids:
                continue
            seen_ids.add(rec.record_id)
            file_path = self.vault_path / rec.path
            if not file_path.exists():
                continue

            if prev_id is not None:
                self._demote_active_node(prev_id)

            try:
                update_frontmatter(file_path, {"cma_active": True})
            except Exception:
                prev_id = None
                continue

            sources_so_far.append(rec.title)
            try:
                write_spec_stub(
                    self.vault_path,
                    spec_id=spec_id,
                    task_id=task_id,
                    query=query,
                    sources_so_far=sources_so_far,
                    retriever_version=__version__,
                )
            except Exception:
                pass

            time.sleep(step_seconds)
            prev_id = rec.record_id

        if prev_id is not None:
            self._demote_active_node(prev_id)

    def _demote_active_node(self, record_id: str) -> None:
        """Clear cma_active on a node and stamp last_retrieved_at + retrieve_count."""
        if not self.vault_path:
            return
        rec = self.records_by_id.get(record_id)
        if rec is None:
            return
        file_path = self.vault_path / rec.path
        if not file_path.exists():
            return
        prev_count = rec.frontmatter.get("retrieve_count", 0)
        try:
            prev_count = int(prev_count)
        except (TypeError, ValueError):
            prev_count = 0
        try:
            update_frontmatter(
                file_path,
                {
                    "cma_active": False,
                    "last_retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "retrieve_count": prev_count + 1,
                },
            )
        except Exception:
            return

    def _touch_visited_notes(self, spec: ContextSpec) -> None:
        """Stamp last_retrieved_at + retrieve_count on each note that contributed.

        Best-effort: a write failure on one note must not break the retrieve.
        Drives the heatmap colorGroups in the Obsidian graph view.
        """
        if not self.vault_path:
            return
        now_iso = datetime.now(timezone.utc).isoformat()
        # Use titles from fragments to look up records, then resolve to file paths.
        seen_ids: set[str] = set()
        for frag in spec.fragments:
            rec = next(
                (r for r in self.records if r.title == frag.source_node),
                None,
            )
            if rec is None or rec.record_id in seen_ids:
                continue
            seen_ids.add(rec.record_id)
            file_path = self.vault_path / rec.path
            if not file_path.exists():
                continue
            prev_count = rec.frontmatter.get("retrieve_count", 0)
            try:
                prev_count = int(prev_count)
            except (TypeError, ValueError):
                prev_count = 0
            try:
                update_frontmatter(
                    file_path,
                    {
                        "last_retrieved_at": now_iso,
                        "retrieve_count": prev_count + 1,
                    },
                )
            except Exception:
                continue

    def _persist_spec_note(self, spec: ContextSpec) -> None:
        """Write the spec to vault/008-context-specs/ as a linked markdown note.

        Best-effort. The wikilinks fan out from the spec node to every source
        when the vault is opened in Obsidian.
        """
        if not self.vault_path:
            return
        try:
            write_spec_to_vault(spec, self.vault_path)
        except Exception:
            pass


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

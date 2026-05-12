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


def per_source_token_artifacts(
    spec, records_by_id, records_by_title=None, vault_path=None
) -> list[dict]:
    """For each unique source in a ContextSpec's fragments, compute how much
    text the Retriever extracted vs the source note's total length.

    Returns a list of artifact dicts suitable for the activity log:
        {
          "title":            "use_gmail_api",
          "path":             "020-sources/email-checker/docs-decisions-use_gmail_api.md",
          "kind":             "source",
          "tokens_extracted": 312,
          "tokens_total":     845,
          "percent":          36.9,
          "fragments":        2,
        }

    Tokens are estimated as len(text) // 4 -- the same approximation used
    elsewhere in CMA (good enough for a dashboard hint; not LLM-exact).
    """
    if not getattr(spec, "fragments", None):
        return []

    # Lookup by title is what fragments reference via source_node.
    if records_by_title is None and records_by_id is not None:
        records_by_title = {r.title: r for r in records_by_id.values()}
    if not records_by_title:
        return []

    per: dict[str, dict] = {}
    for frag in spec.fragments:
        key = frag.source_node
        slot = per.setdefault(key, {"text_chars": 0, "fragments": 0})
        slot["text_chars"] += len(frag.text)
        slot["fragments"] += 1

    spec_id = getattr(spec, "spec_id", None)
    spec_path = f"008-context-specs/{spec_id}.md" if spec_id else None

    out: list[dict] = []
    for title, data in per.items():
        rec = records_by_title.get(title)
        if rec is None:
            continue
        total_chars = max(1, len(rec.body))
        tokens_extracted = max(1, data["text_chars"] // 4)
        tokens_total = max(1, total_chars // 4)
        percent = round(100.0 * data["text_chars"] / total_chars, 1)
        # path may be absolute on disk; reduce to vault-relative for the dashboard link.
        path = rec.path
        if vault_path is not None:
            try:
                from pathlib import Path as _Path
                path = _Path(rec.path).resolve().relative_to(_Path(vault_path).resolve()).as_posix()
            except Exception:
                pass
        entry = {
            "title": title,
            "path": path,
            "kind": "source",
            "tokens_extracted": tokens_extracted,
            "tokens_total": tokens_total,
            "percent": percent,
            "fragments": data["fragments"],
        }
        # The dashboard uses spec_path to render a "view fragments" link that
        # opens the actual spec.md file containing the extracted fragment text
        # for this source under its `### From [[title]]` heading.
        if spec_path:
            entry["spec_path"] = spec_path
        out.append(entry)
    # Sort by tokens extracted descending so the most-mined sources appear first.
    out.sort(key=lambda d: d["tokens_extracted"], reverse=True)
    return out


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
    "per_source_token_artifacts",
]

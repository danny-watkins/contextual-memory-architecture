"""Paragraph-level fragment extraction.

Notes are typically too long to inject whole. The Retriever picks the highest-
signal paragraphs from each candidate node, scores them against the query, and
deduplicates near-identical fragments across nodes.
"""

from __future__ import annotations

import re

from cma.retriever.lexical import tokenize


def split_paragraphs(body: str) -> list[str]:
    """Split a markdown body into non-empty paragraphs.

    Splits on blank lines, strips whitespace, drops empty paragraphs, and
    trims runs of single newlines inside a paragraph. Markdown headers and
    bullet lines stay attached to their paragraph.
    """
    if not body or not body.strip():
        return []
    raw = re.split(r"\n\s*\n", body)
    paragraphs = []
    for chunk in raw:
        cleaned = chunk.strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def score_paragraph(paragraph: str, query_tokens: set[str]) -> float:
    """Score a paragraph by token overlap with the query, normalized to [0, 1].

    This is intentionally lightweight - the Retriever will prefer paragraphs
    from already-high-scoring nodes, so paragraph scoring just picks the best
    paragraph within a chosen note.
    """
    if not query_tokens:
        return 0.0
    para_tokens = set(tokenize(paragraph))
    if not para_tokens:
        return 0.0
    overlap = len(query_tokens & para_tokens)
    return overlap / len(query_tokens)


def select_fragments(
    body: str,
    query: str,
    max_fragments: int = 3,
    min_score: float = 0.0,
) -> list[tuple[str, float]]:
    """Return up to max_fragments (paragraph, score) pairs scored against query.

    Fragments are ranked by score descending. If no paragraph scores above
    min_score, return the first paragraph as a fallback so callers always
    get at least some context.
    """
    paragraphs = split_paragraphs(body)
    if not paragraphs:
        return []
    qtokens = set(tokenize(query))
    scored = [(p, score_paragraph(p, qtokens)) for p in paragraphs]
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = [(p, s) for p, s in scored if s >= min_score][:max_fragments]
    if not selected:
        selected = [(paragraphs[0], 0.0)]
    return selected


def deduplicate_fragments(
    fragments: list[tuple[str, str, float]],
    similarity_threshold: float = 0.85,
) -> list[tuple[str, str, float]]:
    """Remove near-duplicate fragments across nodes.

    Each input is (source_node_id, text, score). Two fragments are considered
    duplicates if their token Jaccard similarity exceeds the threshold. The
    higher-scoring fragment wins.
    """
    if not fragments:
        return []
    sorted_frags = sorted(fragments, key=lambda x: x[2], reverse=True)
    kept: list[tuple[str, str, float, set[str]]] = []
    for src, text, score in sorted_frags:
        tokens = set(tokenize(text))
        is_dup = False
        for _, _, _, existing_tokens in kept:
            if not tokens or not existing_tokens:
                continue
            inter = len(tokens & existing_tokens)
            union = len(tokens | existing_tokens)
            if union and (inter / union) >= similarity_threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append((src, text, score, tokens))
    return [(src, text, score) for src, text, score, _ in kept]

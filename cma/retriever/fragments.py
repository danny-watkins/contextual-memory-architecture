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


_BOILERPLATE_PATTERNS = (
    re.compile(r"^#+\s"),                        # markdown heading: "# notify", "## Sources"
    re.compile(r"^From\s+\[\[[^\]]+\]\]\s*/"),   # ingest attribution: "From [[project]] / path/file.py"
    re.compile(r"^```"),                         # opening/closing code fence on its own line
)


def is_boilerplate(paragraph: str) -> bool:
    """True if the paragraph is structural noise (heading, attribution, fence).

    The Retriever extracts paragraphs as fragments; ingested source files often
    wrap content with a heading line and an attribution line (e.g. "# notify",
    "From [[project]] / skills/notify.py"). Those paragraphs match queries on
    literal keyword overlap ("notify" appears in both) but carry no real content
    and should not be selected over actual body text.
    """
    head = paragraph.lstrip().split("\n", 1)[0].strip()
    return any(p.match(head) for p in _BOILERPLATE_PATTERNS)


def select_fragments(
    body: str,
    query: str,
    max_fragments: int = 3,
    min_score: float = 0.0,
    drop_boilerplate: bool = True,
) -> list[tuple[str, float]]:
    """Return up to max_fragments (paragraph, score) pairs scored against query.

    Fragments are ranked by score descending. When drop_boilerplate=True
    (default), paragraphs that look like structural noise (markdown headings,
    ingest attribution lines, lone code fences) are filtered before scoring;
    they typically match queries on superficial keyword overlap and crowd out
    real content. Set drop_boilerplate=False to disable.

    If no paragraph survives both filters, falls back to the first paragraph
    of non-boilerplate content, then to the first paragraph as a last resort.
    """
    paragraphs = split_paragraphs(body)
    if not paragraphs:
        return []
    pool = [p for p in paragraphs if not (drop_boilerplate and is_boilerplate(p))]
    if not pool:
        pool = paragraphs[:]  # everything was boilerplate; degrade gracefully
    qtokens = set(tokenize(query))
    scored = [(p, score_paragraph(p, qtokens)) for p in pool]
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = [(p, s) for p, s in scored if s >= min_score][:max_fragments]
    if not selected:
        selected = [(pool[0], 0.0)]
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

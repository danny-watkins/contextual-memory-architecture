"""Hybrid scoring + metadata boosts for the Retriever."""

from __future__ import annotations

from cma.retriever.lexical import tokenize
from cma.schemas.memory_record import MemoryRecord


def hybrid_node_score(
    semantic_score: float, lexical_score: float, alpha: float = 0.7
) -> float:
    """Combine semantic and lexical scores into a single node score in [0, 1].

    If semantic_score is 0 (e.g. no embedder configured) the lexical score
    carries the full weight and vice versa - we don't penalize a missing modality.
    """
    if semantic_score <= 0.0 and lexical_score <= 0.0:
        return 0.0
    if semantic_score <= 0.0:
        return lexical_score
    if lexical_score <= 0.0:
        return semantic_score
    return alpha * semantic_score + (1.0 - alpha) * lexical_score


def metadata_boost(record: MemoryRecord) -> float:
    """Multiplicative boost applied to a node's hybrid score based on metadata.

    Boost values follow the whitepaper defaults; a returned 1.0 means no change.
    Negative-direction signals (superseded, stale, substrate, raw code/config)
    reduce the score; positive signals (accepted decisions, human-verified,
    high confidence) raise it.
    """
    boost = 1.0
    if record.type == "decision":
        if record.status == "accepted":
            boost += 0.10
        elif record.status == "superseded":
            boost -= 0.50
        elif record.status == "rejected":
            boost -= 0.30
    if record.status == "archived":
        boost -= 0.20
    if record.human_verified:
        boost += 0.10
    if record.confidence is not None:
        if record.confidence >= 0.85:
            boost += 0.08
        elif record.confidence < 0.30:
            boost -= 0.10
    # Tier penalty: substrate is auto-ingested source material (whitepaper §6.2).
    # Curated memory notes should outrank substrate when other signals are similar,
    # so we tilt the scale at scoring time instead of relying on the user to
    # constantly disambiguate "the company note" from "every config that mentions
    # the company name."
    if record.tier == "substrate":
        boost -= 0.30
    # Structural-content type penalty: raw code/config/data files have dense,
    # rare-keyword payloads (identifiers, string literals, JSON keys) that win
    # lexical scoring on prose queries they have no business answering. Down-weight
    # these types so a semantic prose query lands on a prose note when one exists.
    if record.type in ("code", "config", "data"):
        boost -= 0.15
    return max(0.0, boost)


def title_match_boost(record: MemoryRecord, query: str) -> float:
    """Multiplier rewarding records whose title shares a non-trivial token with
    the query.

    Title match is the strongest, most reliable relevance signal in lexical
    search — far more reliable than body density. Without this, a curated
    `companies/anthropic.md` (title token "anthropic" matches query token
    "anthropic") loses to substrate JSON configs that just happen to mention
    "Anthropic" many times in string-literal payloads.

    Returns 1.0 when no qualifying overlap exists, 6.0 when at least one
    non-trivial query token appears as a title token (case-folded via the
    same tokenizer the BM25 index uses, so behavior is consistent).

    The multiplier is calibrated to let a memory-tier prose note with a
    matching title beat a top-scoring substrate config that mentions the
    query term densely in body text. In the job-tracker dogfood vault, the
    canonical `[[anthropic]]` company note sat at raw BM25 ~0.098 against
    shortlist configs at raw 1.0; the 6× multiplier (with the metadata-tier
    penalty on substrate) is what flips the ranking.
    """
    query_tokens = set(tokenize(query))
    # Filter out very short tokens (e.g. "i", "a") that match too liberally.
    query_tokens = {t for t in query_tokens if len(t) >= 3}
    if not query_tokens:
        return 1.0
    title_tokens = set(tokenize(record.title or ""))
    if query_tokens & title_tokens:
        return 6.0
    return 1.0


def apply_depth_decay(node_score: float, depth: int, decay: float = 0.80) -> float:
    """Multiply a score by decay**depth. Depth 0 (seed nodes) is unaffected."""
    if depth <= 0:
        return node_score
    return node_score * (decay**depth)


def final_score(
    semantic_score: float,
    lexical_score: float,
    record: MemoryRecord,
    depth: int,
    alpha: float = 0.7,
    depth_decay: float = 0.80,
) -> float:
    """Full scoring pipeline: hybrid -> metadata boost -> depth decay."""
    node = hybrid_node_score(semantic_score, lexical_score, alpha)
    boosted = node * metadata_boost(record)
    return apply_depth_decay(boosted, depth, depth_decay)

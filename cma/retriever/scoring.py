"""Hybrid scoring + metadata boosts for the Retriever."""

from __future__ import annotations

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
    Negative-direction signals (superseded, stale) reduce the score; positive
    signals (accepted decisions, human-verified, high confidence) raise it.
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
    return max(0.0, boost)


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

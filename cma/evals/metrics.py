"""Retrieval and memory-quality metrics from whitepaper section 14."""

from __future__ import annotations


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of relevant items that appear in the top-k retrieved.

    Returns 0.0 if `relevant` is empty (we treat that as a query with no
    expected answers and decline to inflate the score).
    """
    if not relevant:
        return 0.0
    top = set(retrieved[:k])
    rel = set(relevant)
    hits = top & rel
    return len(hits) / len(rel)


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of the top-k retrieved that are actually relevant."""
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    rel = set(relevant)
    hits = sum(1 for r in top if r in rel)
    return hits / len(top)


def mrr(retrieved_per_query: list[list[str]], relevant_per_query: list[list[str]]) -> float:
    """Mean Reciprocal Rank: 1 / rank of the first correct answer, averaged.

    Queries with no correct answer in the retrieved list contribute 0.
    """
    if not retrieved_per_query:
        return 0.0
    if len(retrieved_per_query) != len(relevant_per_query):
        raise ValueError("retrieved and relevant lists must align")
    total = 0.0
    for retrieved, relevant in zip(retrieved_per_query, relevant_per_query):
        rel = set(relevant)
        rr = 0.0
        for rank, item in enumerate(retrieved, start=1):
            if item in rel:
                rr = 1.0 / rank
                break
        total += rr
    return total / len(retrieved_per_query)


def memory_usefulness_score(
    relevant_used: int,
    prior_decision_applied: int,
    prior_failure_avoided: int,
    irrelevant_included: int,
    critical_missed: int,
    stale_or_superseded_used: int,
) -> float:
    """Memory Usefulness Score (whitepaper 14.6).

    MUS rewards using the right past memory and penalizes missing critical
    memories or pulling in stale/superseded notes. The exact coefficient
    structure is part of the whitepaper - we expose it so practitioners can
    track the same number across runs.
    """
    return (
        2.0 * relevant_used
        + 2.0 * prior_decision_applied
        + 2.0 * prior_failure_avoided
        - 1.0 * irrelevant_included
        - 3.0 * critical_missed
        - 2.0 * stale_or_superseded_used
    )


def context_efficiency_score(used_fragments: int, included_fragments: int) -> float:
    """Context Efficiency Score (whitepaper 14.7).

    CES = used / included. Higher is better - the Retriever is improving if
    context specs become smaller without degrading task success.
    """
    if included_fragments <= 0:
        return 0.0
    return used_fragments / included_fragments

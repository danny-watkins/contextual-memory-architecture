from cma.retriever.scoring import (
    apply_depth_decay,
    final_score,
    hybrid_node_score,
    metadata_boost,
)
from cma.schemas.memory_record import MemoryRecord


def _rec(**overrides) -> MemoryRecord:
    base = dict(record_id="x", type="note", title="X", path="x.md")
    base.update(overrides)
    return MemoryRecord(**base)


def test_hybrid_default_alpha():
    score = hybrid_node_score(0.8, 0.4, alpha=0.7)
    assert abs(score - (0.7 * 0.8 + 0.3 * 0.4)) < 1e-9


def test_hybrid_zero_lexical_uses_semantic_only():
    assert hybrid_node_score(0.6, 0.0) == 0.6


def test_hybrid_zero_semantic_uses_lexical_only():
    assert hybrid_node_score(0.0, 0.5) == 0.5


def test_hybrid_both_zero():
    assert hybrid_node_score(0.0, 0.0) == 0.0


def test_metadata_boost_accepted_decision():
    rec = _rec(type="decision", status="accepted")
    assert metadata_boost(rec) == 1.10


def test_metadata_boost_superseded_decision():
    rec = _rec(type="decision", status="superseded")
    assert metadata_boost(rec) == 0.50


def test_metadata_boost_human_verified():
    rec = _rec(human_verified=True)
    assert metadata_boost(rec) == 1.10


def test_metadata_boost_high_confidence():
    rec = _rec(confidence=0.9)
    assert abs(metadata_boost(rec) - 1.08) < 1e-9


def test_metadata_boost_low_confidence():
    rec = _rec(confidence=0.2)
    assert abs(metadata_boost(rec) - 0.90) < 1e-9


def test_metadata_boost_archived_penalty():
    rec = _rec(status="archived")
    assert abs(metadata_boost(rec) - 0.80) < 1e-9


def test_metadata_boost_floor_at_zero():
    """Multiple penalties stacking should not produce a negative score."""
    rec = _rec(type="decision", status="superseded", confidence=0.1)
    assert metadata_boost(rec) >= 0.0


def test_metadata_boost_substrate_penalty():
    """Substrate tier (auto-ingested source material) is down-weighted vs memory."""
    rec = _rec(tier="substrate")
    assert abs(metadata_boost(rec) - 0.70) < 1e-9


def test_metadata_boost_memory_tier_unchanged():
    """Memory tier (the default) gets no tier-based adjustment."""
    rec = _rec(tier="memory")
    assert metadata_boost(rec) == 1.0


def test_metadata_boost_code_type_penalty():
    """Raw code files are down-weighted regardless of tier."""
    rec = _rec(type="code")
    assert abs(metadata_boost(rec) - 0.85) < 1e-9


def test_metadata_boost_config_type_penalty():
    """Config/JSON files are down-weighted: rare-keyword density tricks BM25."""
    rec = _rec(type="config")
    assert abs(metadata_boost(rec) - 0.85) < 1e-9


def test_metadata_boost_data_type_penalty():
    rec = _rec(type="data")
    assert abs(metadata_boost(rec) - 0.85) < 1e-9


def test_metadata_boost_substrate_code_stacks():
    """A substrate-tier code file gets both penalties (the common worst case)."""
    rec = _rec(tier="substrate", type="code")
    assert abs(metadata_boost(rec) - 0.55) < 1e-9


def test_metadata_boost_documentation_in_memory_unchanged():
    """The canonical case we're protecting: a curated documentation note in
    tier=memory keeps its full score so it isn't beaten by a substrate config
    that string-matches the query."""
    rec = _rec(type="documentation", tier="memory")
    assert metadata_boost(rec) == 1.0


def test_memory_prose_outranks_substrate_code_with_equal_lexical():
    """Regression test for the Phase 1 testing-suite failure mode.

    Setup mirrors the real `[[anthropic]]` (memory documentation) vs
    `generate_cover_letter` (substrate code) collision: both source notes
    return roughly the same lexical score for the query, but the memory note
    is the one the user actually wants. After the boost, memory must rank
    above substrate-code, not below it.
    """
    memory_note = _rec(type="documentation", tier="memory")
    substrate_code = _rec(type="code", tier="substrate")
    # Give substrate code the *higher* raw lexical match — this is the actual
    # failure mode (cover-letter prompt files have rare keywords, dense matches).
    memory_score = final_score(
        semantic_score=0.45, lexical_score=0.45, record=memory_note, depth=0
    )
    substrate_score = final_score(
        semantic_score=0.50, lexical_score=0.50, record=substrate_code, depth=0
    )
    assert memory_score > substrate_score, (
        f"memory note (score={memory_score}) should outrank substrate code "
        f"(score={substrate_score}) at seed selection; lost to lexical density."
    )


def test_depth_decay_unaffected_at_depth_zero():
    assert apply_depth_decay(0.8, 0) == 0.8


def test_depth_decay_applies_at_depth_one():
    assert abs(apply_depth_decay(1.0, 1, decay=0.8) - 0.8) < 1e-9


def test_depth_decay_compounds():
    assert abs(apply_depth_decay(1.0, 2, decay=0.8) - 0.64) < 1e-9


def test_final_score_pipeline():
    rec = _rec(type="decision", status="accepted", confidence=0.9)
    score = final_score(0.8, 0.4, rec, depth=1, alpha=0.7, depth_decay=0.8)
    expected_node = 0.7 * 0.8 + 0.3 * 0.4
    expected_boosted = expected_node * 1.18  # 1.0 + 0.10 (accepted) + 0.08 (high confidence)
    expected_final = expected_boosted * 0.8  # depth 1 with decay 0.8
    assert abs(score - expected_final) < 1e-9

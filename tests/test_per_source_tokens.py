"""Tests for per_source_token_artifacts -- the helper that breaks down a
ContextSpec into per-source token counts and percentages for the dashboard."""

from datetime import datetime, timezone

from cma.retriever import per_source_token_artifacts
from cma.schemas.context_spec import ContextSpec, Fragment
from cma.schemas.memory_record import MemoryRecord


def _spec(fragments: list[Fragment]) -> ContextSpec:
    return ContextSpec(
        spec_id="spec-test",
        task_id="ad-hoc",
        query="test",
        generated_at=datetime.now(timezone.utc),
        fragments=fragments,
    )


def _record(title: str, body: str) -> MemoryRecord:
    return MemoryRecord(
        record_id=title.lower().replace(" ", "_"),
        title=title,
        type="decision",
        path=f"003-decisions/{title}.md",
        body=body,
        frontmatter={"type": "decision", "title": title},
    )


def test_per_source_basic_one_source_one_fragment():
    """A 100-char fragment from a 400-char source = 25%."""
    rec = _record("Source A", "x" * 400)
    spec = _spec([
        Fragment(
            source_node="Source A", node_type="decision",
            node_score=0.9, fragment_score=0.6, depth=0,
            text="y" * 100,
        ),
    ])
    out = per_source_token_artifacts(spec, {"source_a": rec})
    assert len(out) == 1
    a = out[0]
    assert a["title"] == "Source A"
    assert a["kind"] == "source"
    assert a["fragments"] == 1
    assert a["tokens_extracted"] == 25   # 100 // 4
    assert a["tokens_total"] == 100      # 400 // 4
    assert a["percent"] == 25.0
    # Each source carries a pointer to the spec.md file where its fragments
    # were written -- the dashboard renders a "view fragments" link from this.
    assert a["spec_path"] == "008-context-specs/spec-test.md"


def test_per_source_multiple_fragments_same_source_sum():
    """Two fragments from the same source aggregate into one artifact entry."""
    rec = _record("Source B", "x" * 800)
    spec = _spec([
        Fragment(source_node="Source B", node_type="decision",
                 node_score=0.9, fragment_score=0.6, depth=0, text="y" * 80),
        Fragment(source_node="Source B", node_type="decision",
                 node_score=0.9, fragment_score=0.55, depth=0, text="z" * 40),
    ])
    out = per_source_token_artifacts(spec, {"source_b": rec})
    assert len(out) == 1
    a = out[0]
    assert a["fragments"] == 2
    assert a["tokens_extracted"] == 30   # (80 + 40) // 4
    assert a["tokens_total"] == 200      # 800 // 4
    assert a["percent"] == 15.0


def test_per_source_multiple_sources_sorted_by_tokens_desc():
    """Multiple sources sort with the most-mined one first."""
    rec_a = _record("Small Source", "a" * 200)
    rec_b = _record("Big Source", "b" * 1000)
    spec = _spec([
        Fragment(source_node="Small Source", node_type="decision",
                 node_score=0.5, fragment_score=0.5, depth=0, text="x" * 40),
        Fragment(source_node="Big Source", node_type="decision",
                 node_score=0.8, fragment_score=0.6, depth=0, text="y" * 200),
    ])
    out = per_source_token_artifacts(
        spec, {"small_source": rec_a, "big_source": rec_b}
    )
    assert len(out) == 2
    assert out[0]["title"] == "Big Source"
    assert out[1]["title"] == "Small Source"


def test_per_source_skips_missing_records():
    """If a fragment references a source not in the records dict, skip it."""
    rec = _record("Known", "k" * 400)
    spec = _spec([
        Fragment(source_node="Known", node_type="decision",
                 node_score=0.9, fragment_score=0.6, depth=0, text="x" * 100),
        Fragment(source_node="Ghost", node_type="decision",
                 node_score=0.9, fragment_score=0.6, depth=0, text="x" * 50),
    ])
    out = per_source_token_artifacts(spec, {"known": rec})
    assert len(out) == 1
    assert out[0]["title"] == "Known"


def test_per_source_empty_spec_returns_empty():
    """No fragments = no artifacts."""
    spec = _spec([])
    assert per_source_token_artifacts(spec, {}) == []

"""Tests for the persisted-spec wikilink caps that keep context_spec notes
from becoming graph mega-hubs."""

from datetime import datetime, timezone

from cma.retriever.spec_builder import (
    RELATIONSHIP_WIKILINK_CAP,
    SOURCE_WIKILINK_CAP,
    render_spec_as_vault_note,
)
from cma.schemas.context_spec import ContextSpec, Exclusion, Fragment, RelationshipEdge


def _spec_with_n_sources(n: int) -> ContextSpec:
    fragments = [
        Fragment(
            source_node=f"src-{i:03d}",
            node_type="documentation",
            node_score=0.5,
            fragment_score=0.5,
            depth=1,
            text=f"fragment body {i}",
        )
        for i in range(n)
    ]
    edges = [
        RelationshipEdge(source=f"src-{i:03d}", target=f"src-{i+1:03d}")
        for i in range(n - 1)
    ]
    return ContextSpec(
        spec_id="spec-test",
        task_id="t1",
        query="cap test",
        generated_at=datetime.now(timezone.utc),
        fragments=fragments,
        relationship_map=edges,
    )


def test_source_wikilinks_are_capped():
    """A spec citing 30 sources should only emit SOURCE_WIKILINK_CAP wikilinks
    under ## Sources; the rest appear as plain titles. Without this cap,
    spec_builder writes 30 [[wikilinks]] and the spec becomes a 30-edge hub."""
    spec = _spec_with_n_sources(30)
    note = render_spec_as_vault_note(spec)
    sources_block = note.split("## Sources", 1)[1].split("##", 1)[0]
    wikilinks = sources_block.count("[[")
    assert wikilinks == SOURCE_WIKILINK_CAP, (
        f"expected {SOURCE_WIKILINK_CAP} wikilinks under ## Sources, got {wikilinks}"
    )
    # And the overflowed sources still appear in the body for human readability.
    assert "src-029" in note
    assert "+ 22 more" in note


def test_relationship_map_wikilinks_are_capped():
    """The relationship map emits 2 wikilinks per edge (source + target), so
    without a cap a 100-edge map contributes 200 visible graph edges."""
    spec = _spec_with_n_sources(50)
    note = render_spec_as_vault_note(spec)
    rel_block = note.split("## Relationship Map", 1)[1]
    # Each capped edge line has the form "- [[X]] -> [[Y]] (wikilink)".
    capped_edge_lines = [
        ln for ln in rel_block.splitlines()
        if ln.startswith("- [[") and "-> [[" in ln
    ]
    assert len(capped_edge_lines) == RELATIONSHIP_WIKILINK_CAP


def test_small_spec_is_unchanged_by_cap():
    """Specs below the cap should render with the full list of wikilinks and
    no 'N more' overflow message."""
    spec = _spec_with_n_sources(3)
    note = render_spec_as_vault_note(spec)
    assert note.count("[[src-") >= 3
    assert "more (listed without wikilinks" not in note


def test_exclusions_also_capped():
    """Exclusions list was a third unbounded wikilink emitter."""
    spec = _spec_with_n_sources(2)
    spec.exclusions = [Exclusion(node=f"excl-{i:03d}", reason="off-topic") for i in range(20)]
    note = render_spec_as_vault_note(spec)
    excl_block = note.split("## Exclusions", 1)[1]
    wikilinks = excl_block.count("[[")
    assert wikilinks == SOURCE_WIKILINK_CAP

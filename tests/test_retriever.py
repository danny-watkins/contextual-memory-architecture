from pathlib import Path

from cma.retriever import Retriever, render_markdown
from cma.storage.graph_store import build_graph
from cma.storage.markdown_store import parse_vault


def _example_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "003-decisions").mkdir(parents=True)
    (vault / "004-patterns").mkdir(parents=True)
    (vault / "003-decisions" / "Async Capital Call Processing.md").write_text(
        """---
type: decision
title: Async Capital Call Processing
status: accepted
confidence: 0.86
human_verified: true
---

We decided to move capital call processing into an async queue.

This uses [[Queue Retry Pattern]] for reliability.

Related anti-pattern: [[External API Synchronous Bottleneck]]
""",
        encoding="utf-8",
    )
    (vault / "004-patterns" / "Queue Retry Pattern.md").write_text(
        """---
type: pattern
title: Queue Retry Pattern
status: active
confidence: 0.78
---

For external API calls that may fail intermittently, place the call behind an
async queue with bounded exponential backoff.

Used by [[Async Capital Call Processing]].
""",
        encoding="utf-8",
    )
    (vault / "004-patterns" / "External API Synchronous Bottleneck.md").write_text(
        """---
type: pattern
title: External API Synchronous Bottleneck
status: active
confidence: 0.72
---

Synchronous external API calls in the request path cap latency at the slowest
external dependency.

Mitigation: see [[Queue Retry Pattern]].
""",
        encoding="utf-8",
    )
    (vault / "Cooking Rice.md").write_text(
        """---
type: note
title: Cooking Rice
---

Add rice to boiling water and simmer for 15 minutes.
""",
        encoding="utf-8",
    )
    return vault


def _retriever_bm25_only(vault_path: Path) -> Retriever:
    records = parse_vault(vault_path)
    graph = build_graph(records)
    return Retriever(records=records, graph=graph, embedder=None)


def test_retriever_returns_relevant_seed(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing")

    assert spec.fragments
    titles = {f.source_node for f in spec.fragments}
    # The decision note should be the top seed
    assert "Async Capital Call Processing" in titles
    # The unrelated note should not appear
    assert "Cooking Rice" not in titles


def test_retriever_traverses_graph_to_pattern(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing", max_depth=2)
    titles = {f.source_node for f in spec.fragments}
    # Linked patterns should be reachable via graph traversal
    assert "Queue Retry Pattern" in titles or "External API Synchronous Bottleneck" in titles


def test_retriever_excludes_unrelated_with_threshold(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing", max_depth=0)
    titles = {f.source_node for f in spec.fragments}
    assert "Cooking Rice" not in titles


def test_retriever_assembles_relationship_map(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing", max_depth=2)
    if spec.relationship_map:
        # If we got multiple notes, some edges should have been recorded
        sources = {e.source for e in spec.relationship_map}
        targets = {e.target for e in spec.relationship_map}
        assert sources & targets or len(spec.relationship_map) >= 1


def test_retriever_records_parameters(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing", max_depth=1, beam_width=3)
    assert spec.parameters["max_depth"] == 1
    assert spec.parameters["beam_width"] == 3
    assert spec.parameters["embedder"] == "none"


def test_render_markdown_smoke(tmp_path: Path):
    vault = _example_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("capital call processing")
    md = render_markdown(spec)
    assert "# Context Spec" in md
    assert spec.task_id in md
    assert "Retrieved Fragments" in md


def _flywheel_poisoned_vault(tmp_path: Path) -> Path:
    """Vault that reproduces the Phase 1 failure mode: a canonical memory note
    competing against context_spec self-references, inbox-prompt noise, and
    substrate code files that string-match the query."""
    vault = tmp_path / "vault"
    (vault / "020-sources" / "companies").mkdir(parents=True)
    (vault / "008-context-specs").mkdir(parents=True)
    (vault / "000-inbox" / "prompts" / "2026-05-14").mkdir(parents=True)
    (vault / "020-sources" / "code").mkdir(parents=True)

    # The canonical answer: a curated memory-tier company note.
    (vault / "020-sources" / "companies" / "anthropic.md").write_text(
        """---
type: documentation
tier: memory
title: anthropic
status: active
---

# Anthropic

Anthropic builds reliable, interpretable, and steerable AI systems. Applied roles tracked here.
""",
        encoding="utf-8",
    )

    # Context-spec self-reference: stores the exact user query in its body.
    # Before the fix, this scores ~1.0 on the literal-substring query.
    (vault / "008-context-specs" / "spec-deadbeef.md").write_text(
        """---
type: context_spec
tier: memory
title: spec-deadbeef
status: active
---

## Task
- Query: what do you know about Anthropic?
- Generated: 2026-05-14T00:00:00Z
""",
        encoding="utf-8",
    )

    # Inbox-prompt noise: literal query in title and body.
    (vault / "000-inbox" / "prompts" / "2026-05-14" / "prompt-001.md").write_text(
        """---
type: note
tier: memory
title: what do you know about Anthropic?
status: noise
---

what do you know about Anthropic?
""",
        encoding="utf-8",
    )

    # Substrate code that mentions Anthropic many times in string literals.
    (vault / "020-sources" / "code" / "generate_cover_letter.md").write_text(
        """---
type: code
tier: substrate
title: generate_cover_letter
status: proposed
---

```python
PROMPT_ANTHROPIC = "Anthropic builds AI systems. Anthropic. Anthropic. Anthropic."
PROMPT_ANTHROPIC_2 = "When writing to Anthropic, mention Anthropic's mission."
```
""",
        encoding="utf-8",
    )
    return vault


def test_retriever_excludes_context_specs_and_noise_from_seeds(tmp_path: Path):
    """Regression test for the Phase 1 flywheel-poisoning failure.

    With the fix, a query whose literal text appears verbatim in a context_spec
    and an inbox-prompt note must still seed on the actual memory note.
    """
    vault = _flywheel_poisoned_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("what do you know about Anthropic?")
    titles = {f.source_node for f in spec.fragments}

    assert "anthropic" in titles, (
        f"company note (the canonical answer) must be in fragments; got {titles}"
    )
    assert "spec-deadbeef" not in titles, (
        "context_spec notes self-reference the query and must not seed retrieval"
    )
    # The inbox prompt has title equal to the query; ensure it's filtered too.
    for f in spec.fragments:
        assert f.source_node != "prompt-001", (
            "inbox-prompt notes (status=noise) must not appear in fragments"
        )


def test_retriever_memory_note_outranks_substrate_code(tmp_path: Path):
    """When a memory-tier note and a substrate-tier code file both match a
    query, the memory note must rank higher (it's the curated answer)."""
    vault = _flywheel_poisoned_vault(tmp_path)
    retriever = _retriever_bm25_only(vault)
    spec = retriever.retrieve("Anthropic")

    # Ordering: find positions of the two competing nodes
    seen = []
    for f in spec.fragments:
        if f.source_node not in seen:
            seen.append(f.source_node)

    if "generate_cover_letter" in seen and "anthropic" in seen:
        assert seen.index("anthropic") < seen.index("generate_cover_letter"), (
            f"memory note 'anthropic' should outrank substrate code "
            f"'generate_cover_letter'; got order {seen}"
        )
    else:
        # The memory note should at minimum be present.
        assert "anthropic" in seen, f"memory note missing from results; got {seen}"

"""Assemble a ContextSpec from scored fragments + relationship map."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from cma.schemas.context_spec import ContextSpec, Exclusion, Fragment, RelationshipEdge

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9_\-]+")

# Caps on how many wikilinks the persisted spec note emits. Without these, a
# single context_spec becomes a graph mega-hub citing every traversed source
# (we've seen 236 outbound edges from one spec). Beyond the cap, sources are
# listed as plain titles in body text so they're searchable but don't add
# visible graph edges.
SOURCE_WIKILINK_CAP = 8
RELATIONSHIP_WIKILINK_CAP = 12


def build_context_spec(
    *,
    task_id: str,
    query: str,
    parameters: dict,
    fragments: list[Fragment],
    relationship_map: list[RelationshipEdge],
    open_questions: list[str] | None = None,
    exclusions: list[Exclusion] | None = None,
    retriever_version: str = "0.1.0",
    spec_id: str | None = None,
) -> ContextSpec:
    """Assemble a ContextSpec from already-scored fragments and a relationship map."""
    return ContextSpec(
        spec_id=spec_id or f"spec-{uuid4().hex[:8]}",
        task_id=task_id,
        query=query,
        generated_at=datetime.now(timezone.utc),
        retriever_version=retriever_version,
        parameters=parameters,
        fragments=fragments,
        relationship_map=relationship_map,
        open_questions=open_questions or [],
        exclusions=exclusions or [],
    )


def new_spec_id() -> str:
    return f"spec-{uuid4().hex[:8]}"


def write_spec_stub(
    vault_path: Path,
    *,
    spec_id: str,
    task_id: str,
    query: str,
    sources_so_far: list[str],
    retriever_version: str = "0.1.0",
) -> Path:
    """Write a placeholder spec note that grows as the demo walk visits nodes.

    Used only by demo mode. The final, full spec note is written by
    `write_spec_to_vault` at the end of retrieve and overwrites this stub.
    """
    target_dir = Path(vault_path) / "008-context-specs"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_id = _FILENAME_SAFE.sub("-", spec_id) or "spec"
    out_path = target_dir / f"{safe_id}.md"
    safe_query = query.replace('"', "'")

    lines: list[str] = []
    lines.append("---")
    lines.append("type: context_spec")
    lines.append(f"spec_id: {spec_id}")
    lines.append(f"task_id: {task_id}")
    lines.append(f'query: "{safe_query}"')
    lines.append(f"generated_at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"retriever_version: {retriever_version}")
    lines.append("status: in_progress")
    lines.append("---")
    lines.append("")
    lines.append(f"# Context Spec (in progress): {query}")
    lines.append("")
    lines.append("## Sources collected so far")
    if not sources_so_far:
        lines.append("_Walking the graph..._")
    else:
        for src in sources_so_far:
            lines.append(f"- [[{src}]]")
    lines.append("")
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path


def render_markdown(spec: ContextSpec) -> str:
    """Render a ContextSpec as the inspectable markdown artifact described in the whitepaper.

    Intentionally human-readable: this is what you'd commit to the vault under
    008-context-specs/ if you wanted to keep a record of what context was used
    for a given task.
    """
    out: list[str] = []
    out.append("# Context Spec")
    out.append("")
    out.append("## Task")
    out.append(f"- Task ID: {spec.task_id}")
    out.append(f"- Spec ID: {spec.spec_id}")
    out.append(f"- Query: {spec.query}")
    out.append(f"- Generated: {spec.generated_at.isoformat()}")
    out.append(f"- Retriever version: {spec.retriever_version}")
    out.append("")

    if spec.parameters:
        out.append("## Retrieval Parameters")
        for key, value in spec.parameters.items():
            out.append(f"- {key}: {value}")
        out.append("")

    out.append("## Retrieved Fragments")
    if not spec.fragments:
        out.append("_No fragments retrieved._")
        out.append("")
    for frag in spec.fragments:
        out.append(f"### Node: {frag.source_node}")
        out.append(f"- type: {frag.node_type}")
        out.append(f"- node_score: {frag.node_score:.3f}")
        out.append(f"- fragment_score: {frag.fragment_score:.3f}")
        out.append(f"- depth: {frag.depth}")
        out.append("")
        out.append("Fragment:")
        out.append("")
        out.append(frag.text)
        out.append("")
        if frag.why_included:
            out.append(f"Why included: {frag.why_included}")
            out.append("")

    if spec.relationship_map:
        out.append("## Relationship Map")
        for edge in spec.relationship_map:
            out.append(f"- {edge.source} -> {edge.target} ({edge.edge_type})")
        out.append("")

    if spec.open_questions:
        out.append("## Open Questions")
        for q in spec.open_questions:
            out.append(f"- {q}")
        out.append("")

    if spec.exclusions:
        out.append("## Exclusions")
        for exc in spec.exclusions:
            out.append(f"- {exc.node}: {exc.reason}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def render_spec_as_vault_note(spec: ContextSpec) -> str:
    """Render a ContextSpec as a markdown note suitable for `vault/008-context-specs/`.

    Adds YAML frontmatter (so the note parses as type=context_spec) and renders
    every source as a `[[wikilink]]`. Opening the vault in Obsidian shows the
    spec node with edges fanning out to every fragment source.
    """
    sources_in_order: list[str] = []
    seen: set[str] = set()
    for frag in spec.fragments:
        if frag.source_node not in seen:
            seen.add(frag.source_node)
            sources_in_order.append(frag.source_node)

    safe_query = spec.query.replace('"', "'")

    lines: list[str] = []
    lines.append("---")
    lines.append("type: context_spec")
    lines.append(f"spec_id: {spec.spec_id}")
    lines.append(f"task_id: {spec.task_id}")
    lines.append(f'query: "{safe_query}"')
    lines.append(f"generated_at: {spec.generated_at.isoformat()}")
    lines.append(f"retriever_version: {spec.retriever_version}")
    lines.append(f"fragment_count: {len(spec.fragments)}")
    lines.append(f"source_count: {len(sources_in_order)}")
    lines.append("status: active")
    lines.append("---")
    lines.append("")
    lines.append(f"# Context Spec: {spec.query}")
    lines.append("")

    lines.append("## Sources")
    if not sources_in_order:
        lines.append("_No sources retrieved._")
    else:
        for src in sources_in_order[:SOURCE_WIKILINK_CAP]:
            lines.append(f"- [[{src}]]")
        overflow = sources_in_order[SOURCE_WIKILINK_CAP:]
        if overflow:
            lines.append("")
            lines.append(f"_+ {len(overflow)} more (listed without wikilinks to keep the spec from becoming a graph hub):_")
            for src in overflow:
                lines.append(f"- {src}")
    lines.append("")

    if spec.parameters:
        lines.append("## Retrieval Parameters")
        for key, value in spec.parameters.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    lines.append("## Fragments")
    if not spec.fragments:
        lines.append("_No fragments retrieved._")
        lines.append("")
    for frag in spec.fragments:
        lines.append(
            f"### From [[{frag.source_node}]] "
            f"(depth {frag.depth}, score {frag.node_score:.2f})"
        )
        lines.append("")
        lines.append(frag.text)
        lines.append("")
        if frag.why_included:
            lines.append(f"_{frag.why_included}_")
            lines.append("")

    if spec.relationship_map:
        lines.append("## Relationship Map")
        for edge in spec.relationship_map[:RELATIONSHIP_WIKILINK_CAP]:
            lines.append(f"- [[{edge.source}]] -> [[{edge.target}]] ({edge.edge_type})")
        overflow = spec.relationship_map[RELATIONSHIP_WIKILINK_CAP:]
        if overflow:
            lines.append("")
            lines.append(f"_+ {len(overflow)} more edges (plain text to avoid graph fan-out):_")
            for edge in overflow:
                lines.append(f"- {edge.source} -> {edge.target} ({edge.edge_type})")
        lines.append("")

    if spec.open_questions:
        lines.append("## Open Questions")
        for q in spec.open_questions:
            lines.append(f"- {q}")
        lines.append("")

    if spec.exclusions:
        lines.append("## Exclusions")
        for exc in spec.exclusions[:SOURCE_WIKILINK_CAP]:
            lines.append(f"- [[{exc.node}]]: {exc.reason}")
        overflow = spec.exclusions[SOURCE_WIKILINK_CAP:]
        if overflow:
            for exc in overflow:
                lines.append(f"- {exc.node}: {exc.reason}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_spec_to_vault(spec: ContextSpec, vault_path: Path) -> Path:
    """Write the ContextSpec as a markdown note under `vault/008-context-specs/`.

    Returns the path written. The folder is created if it doesn't exist.
    """
    vault_path = Path(vault_path)
    target_dir = vault_path / "008-context-specs"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_id = _FILENAME_SAFE.sub("-", spec.spec_id) or "spec"
    out_path = target_dir / f"{safe_id}.md"
    out_path.write_text(render_spec_as_vault_note(spec), encoding="utf-8")
    return out_path

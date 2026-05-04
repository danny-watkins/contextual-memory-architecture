"""Assemble a ContextSpec from scored fragments + relationship map."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from cma.schemas.context_spec import ContextSpec, Exclusion, Fragment, RelationshipEdge


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
) -> ContextSpec:
    """Assemble a ContextSpec from already-scored fragments and a relationship map."""
    return ContextSpec(
        spec_id=f"spec-{uuid4().hex[:8]}",
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

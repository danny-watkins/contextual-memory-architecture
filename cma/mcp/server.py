"""MCP server exposing CMA primitives as tools for any MCP-aware agent.

Exposes ten tools, split into two layers:

Graph primitives (composable, fine-grained):
    search_notes(query, top_k)             - hybrid BM25 + embedding search
    get_note(title)                         - fetch full note content
    get_outgoing_links(title)               - notes this note links to
    get_backlinks(title)                    - notes that link to this note
    traverse_graph(start, depth)            - notes within N hops of a start
    search_by_frontmatter(key, value)       - filter by YAML metadata

Higher-level orchestrators (one-shot pipelines):
    retrieve(query, max_depth, beam_width)  - full Retriever pipeline -> Context Spec markdown
    record_completion(yaml_str, dry_run)    - Recorder ingestion
    graph_health()                          - graph structure report
    reindex()                               - refresh BM25 + embeddings after vault changes

Transport: stdio (the format Claude Code expects). Start with:
    cma mcp serve --project /path/to/your/cma-project
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "MCP support is not installed. "
        "Install with: pip install 'contextual-memory-architecture[mcp]'"
    ) from e

from cma.activity import log_activity
from cma.recorder import Recorder
from cma.retriever import Retriever, per_source_token_artifacts, render_markdown
from cma.retriever.traversal import traverse
from cma.schemas.completion_package import CompletionPackage
from cma.schemas.memory_record import MemoryRecord
from cma.storage.graph_store import graph_health_report

# ---- module-level state held for the lifetime of the server process ----

_PROJECT_PATH: Path | None = None
_RETRIEVER: Retriever | None = None
_RECORDER: Recorder | None = None

mcp = FastMCP("cma")


def _ensure_loaded() -> None:
    """Lazily initialize Retriever and Recorder. Called on every tool."""
    global _RETRIEVER, _RECORDER
    if _PROJECT_PATH is None:
        raise RuntimeError("CMA MCP server not initialized. Run via `cma mcp serve --project <path>`.")
    if _RETRIEVER is None:
        _RETRIEVER = Retriever.from_project(_PROJECT_PATH)
    if _RECORDER is None:
        _RECORDER = Recorder.from_project(_PROJECT_PATH)


def _find_record(title_or_id: str) -> MemoryRecord | None:
    """Resolve a wikilink-style title or filename stem to a MemoryRecord."""
    assert _RETRIEVER is not None
    needle = title_or_id.lower().strip()
    for rec in _RETRIEVER.records:
        if rec.title.lower() == needle or rec.record_id.lower() == needle:
            return rec
    return None


def _node_title(node_id: str) -> str:
    """Get the human-readable title for a graph node id."""
    assert _RETRIEVER is not None
    return _RETRIEVER.graph.nodes[node_id].get("title", node_id)


# ---- graph primitives ----


@mcp.tool()
def search_notes(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Hybrid (BM25 + embeddings) search over note titles and bodies.

    Returns the top_k matching notes ordered by relevance score. Use this to
    seed a multi-hop walk: agents typically call this first, then expand
    outward with get_outgoing_links / get_backlinks / traverse_graph.
    """
    import time as _time
    _ensure_loaded()
    assert _RETRIEVER is not None
    started = _time.perf_counter()
    seeds = _RETRIEVER._select_seeds(
        query, top_k=top_k, alpha=_RETRIEVER.config.alpha, node_threshold=0.0
    )
    out: list[dict[str, Any]] = []
    for record_id, score in seeds:
        rec = _RETRIEVER.records_by_id.get(record_id)
        if rec is None:
            continue
        out.append(
            {
                "title": rec.title,
                "type": rec.type,
                "score": round(score, 4),
                "path": rec.path,
                "tags": rec.tags,
            }
        )
    duration_ms = (_time.perf_counter() - started) * 1000
    log_activity(
        _PROJECT_PATH, "search",
        duration_ms=duration_ms,
        query=query,
        summary=f'"{query}" -> {len(out)} hits' + (f', top {out[0]["score"]:.2f}' if out else ""),
        details={"top_k": top_k, "results": [{"title": h["title"], "score": h["score"], "type": h["type"]} for h in out]},
    )
    return out


@mcp.tool()
def get_note(title: str) -> dict[str, Any] | None:
    """Fetch a note's full body, frontmatter, and links by title or filename stem."""
    _ensure_loaded()
    rec = _find_record(title)
    if rec is None:
        return None
    return {
        "title": rec.title,
        "type": rec.type,
        "status": rec.status,
        "path": rec.path,
        "body": rec.body,
        "frontmatter": rec.frontmatter,
        "links": rec.links,
        "tags": rec.tags,
        "confidence": rec.confidence,
        "domain": rec.domain,
    }


@mcp.tool()
def get_outgoing_links(title: str) -> list[str]:
    """List the titles of notes this note links to via wikilinks."""
    _ensure_loaded()
    assert _RETRIEVER is not None
    rec = _find_record(title)
    if rec is None:
        return []
    return [
        _node_title(succ)
        for succ in _RETRIEVER.graph.successors(rec.record_id)
        if _RETRIEVER.graph.nodes[succ].get("exists", False)
    ]


@mcp.tool()
def get_backlinks(title: str) -> list[str]:
    """List the titles of notes that link TO this note."""
    _ensure_loaded()
    assert _RETRIEVER is not None
    rec = _find_record(title)
    if rec is None:
        return []
    return [
        _node_title(pred)
        for pred in _RETRIEVER.graph.predecessors(rec.record_id)
        if _RETRIEVER.graph.nodes[pred].get("exists", False)
    ]


@mcp.tool()
def traverse_graph(start: str, depth: int = 2) -> list[dict[str, Any]]:
    """Return notes within `depth` hops of the start note (forward and backward edges)."""
    _ensure_loaded()
    assert _RETRIEVER is not None
    rec = _find_record(start)
    if rec is None:
        return []
    candidates = traverse(
        _RETRIEVER.graph, [(rec.record_id, 1.0)], max_depth=depth, beam_width=50
    )
    return [
        {
            "title": _node_title(c.node_id),
            "depth": c.depth,
            "type": _RETRIEVER.graph.nodes[c.node_id].get("type", "note"),
        }
        for c in candidates
    ]


@mcp.tool()
def search_by_frontmatter(key: str, value: str) -> list[dict[str, Any]]:
    """Filter notes by YAML frontmatter. Substring match on string values; membership for lists."""
    _ensure_loaded()
    assert _RETRIEVER is not None
    needle = value.lower()
    out: list[dict[str, Any]] = []
    for rec in _RETRIEVER.records:
        v = rec.frontmatter.get(key)
        if v is None:
            continue
        match = False
        if isinstance(v, list):
            match = any(needle in str(item).lower() for item in v)
        else:
            match = needle in str(v).lower()
        if match:
            out.append(
                {
                    "title": rec.title,
                    "type": rec.type,
                    "path": rec.path,
                    "value": v,
                }
            )
    return out


# ---- higher-level orchestrators ----


@mcp.tool()
def retrieve(
    query: str,
    max_depth: int = 2,
    beam_width: int = 5,
) -> str:
    """Full Retriever pipeline: hybrid seed search + graph traversal + fragment extraction.

    Returns a rendered Context Spec in markdown form, ready to drop into a prompt.
    Use this when you want one-shot retrieval; use the lower-level primitives
    when you want to drive the walk yourself (mid-inference tool calls).
    """
    import time as _time
    _ensure_loaded()
    assert _RETRIEVER is not None
    started = _time.perf_counter()
    spec = _RETRIEVER.retrieve(query, max_depth=max_depth, beam_width=beam_width)
    duration_ms = (_time.perf_counter() - started) * 1000

    artifacts: list[dict] = []
    spec_id = spec.spec_id
    if spec_id:
        artifacts.append({
            "title": spec_id,
            "path": f"008-context-specs/{spec_id}.md",
            "kind": "spec",
        })
    # Per-source token artifacts: for each source node the retriever pulled
    # fragments from, how many tokens it extracted and what fraction of the
    # source note's total token count that represents. Surfaces in the dashboard
    # as "use_gmail_api · 312 tokens · 37% of doc".
    source_artifacts = per_source_token_artifacts(
        spec, _RETRIEVER.records_by_id, vault_path=_RETRIEVER.vault_path
    )
    artifacts.extend(source_artifacts)
    total_tokens_pulled = sum(a.get("tokens_extracted", 0) for a in source_artifacts)

    log_activity(
        _PROJECT_PATH, "retrieve",
        duration_ms=duration_ms,
        query=query,
        summary=f'"{query}" -> {len(source_artifacts)} sources, {total_tokens_pulled} tokens, depth {max_depth}',
        artifacts=artifacts,
        details={
            "max_depth": max_depth,
            "beam_width": beam_width,
            "n_sources": len(source_artifacts),
            "n_fragments": len(spec.fragments),
            "total_tokens_extracted": total_tokens_pulled,
        },
    )
    return render_markdown(spec)


def _vault_relative(path: str) -> str:
    """Best-effort: convert an absolute vault path to a vault-relative one."""
    if _PROJECT_PATH is None:
        return path
    p = Path(path)
    vault = _PROJECT_PATH / "cma" / "vault"
    try:
        return p.resolve().relative_to(vault.resolve()).as_posix()
    except ValueError:
        return path


@mcp.tool()
def record_completion(
    completion_package_yaml: str, dry_run: bool = False
) -> dict[str, Any]:
    """Ingest a CompletionPackage (as a YAML string) and write structured memory.

    Returns counts of written / proposed / skipped items and their paths.
    Set dry_run=True to preview without touching disk.
    """
    import time as _time
    _ensure_loaded()
    assert _RECORDER is not None
    started = _time.perf_counter()
    data = yaml.safe_load(completion_package_yaml)
    package = CompletionPackage(**data)
    result = _RECORDER.record_completion(package, dry_run=dry_run)
    duration_ms = (_time.perf_counter() - started) * 1000

    if not dry_run:
        artifacts: list[dict[str, str]] = []
        for p in result.written:
            p_obj = Path(p)
            kind = "decision" if "003-decisions" in p_obj.as_posix() else \
                   "pattern" if "004-patterns" in p_obj.as_posix() else \
                   "session" if "002-sessions" in p_obj.as_posix() else \
                   "daily" if "010-daily-log" in p_obj.as_posix() else "note"
            artifacts.append({"title": p_obj.stem, "path": _vault_relative(str(p)), "kind": kind})
        for p in result.proposed:
            p_obj = Path(p)
            artifacts.append({"title": p_obj.stem, "path": _vault_relative(str(p)), "kind": "proposed"})
        log_activity(
            _PROJECT_PATH, "record",
            duration_ms=duration_ms,
            task_id=package.task_id,
            summary=f"task: {package.task_id} -> {len(result.written)} written, {len(result.proposed)} proposed, {len(result.skipped)} skipped",
            artifacts=artifacts,
            details={"written": len(result.written), "proposed": len(result.proposed), "skipped": len(result.skipped)},
        )

    return {
        "summary": result.summary(),
        "written": [str(p) for p in result.written],
        "proposed": [str(p) for p in result.proposed],
        "skipped": [{"item": label, "reason": reason} for label, reason in result.skipped],
    }


@mcp.tool()
def graph_health() -> dict[str, Any]:
    """Return a structural health report for the memory graph."""
    _ensure_loaded()
    assert _RETRIEVER is not None
    return graph_health_report(_RETRIEVER.graph)


@mcp.tool()
def reindex() -> dict[str, Any]:
    """Re-parse the vault and rebuild Retriever in-memory state.

    Call this after the Recorder has written new notes so subsequent retrieve()
    calls see them. Note: this rebuilds in-memory only; on-disk .cma/ artifacts
    are refreshed separately by `cma index` from the CLI.
    """
    global _RETRIEVER, _RECORDER
    if _PROJECT_PATH is None:
        raise RuntimeError("Server not initialized.")
    _RETRIEVER = Retriever.from_project(_PROJECT_PATH)
    _RECORDER = Recorder.from_project(_PROJECT_PATH)
    return {
        "status": "rebuilt",
        "n_records": len(_RETRIEVER.records),
        "n_edges": _RETRIEVER.graph.number_of_edges(),
    }


# ---- entry point ----


def run_server(project_path: Path) -> None:
    """Run the MCP server over stdio. Retriever/Recorder load lazily on first tool call."""
    global _PROJECT_PATH
    _PROJECT_PATH = Path(project_path).resolve()
    # Log to stderr so it doesn't pollute the stdio JSON-RPC stream.
    # Heavy init (embedding model, BM25) is deferred to the first tool call so the
    # MCP `initialize` handshake completes within the client's connect timeout.
    print(f"[cma] MCP server ready (project={_PROJECT_PATH}, lazy init)", file=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CMA MCP server")
    parser.add_argument("--project", required=True, type=Path, help="Path to the CMA project")
    args = parser.parse_args()
    run_server(args.project)

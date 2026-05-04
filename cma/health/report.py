"""Compute the memory-health report for a CMA project."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import networkx as nx

from cma.config import CMAConfig
from cma.storage.graph_store import build_graph
from cma.storage.markdown_store import parse_vault, walk_vault

# Soft thresholds: above these, the report emits warnings.
THRESHOLDS = {
    "vault_notes": 50_000,
    "embeddings_bytes": 200 * 1024 * 1024,
    "orphan_rate": 0.30,
    "broken_link_rate": 0.05,
    "never_retrieved_rate": 0.70,
}


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def _vault_breakdown(vault_path: Path) -> dict[str, Any]:
    by_folder: dict[str, dict[str, int]] = {}
    total_bytes = 0
    total_notes = 0
    for md in walk_vault(vault_path):
        rel = md.relative_to(vault_path)
        folder = rel.parts[0] if len(rel.parts) > 1 else "."
        size = md.stat().st_size
        bucket = by_folder.setdefault(folder, {"notes": 0, "bytes": 0})
        bucket["notes"] += 1
        bucket["bytes"] += size
        total_notes += 1
        total_bytes += size
    return {
        "total_notes": total_notes,
        "total_bytes": total_bytes,
        "by_folder": dict(sorted(by_folder.items())),
    }


def _graph_breakdown(graph: nx.DiGraph) -> dict[str, Any]:
    existing = [n for n, d in graph.nodes(data=True) if d.get("exists", False)]
    n = len(existing)
    if n == 0:
        return {
            "total_nodes": 0,
            "total_edges": 0,
            "average_out_degree": 0.0,
            "orphans": 0,
            "orphan_rate": 0.0,
            "broken_links": 0,
            "broken_link_rate": 0.0,
        }

    out_deg = sum(graph.out_degree(node) for node in existing) / n

    orphans: list[str] = []
    for node in existing:
        in_existing = any(graph.nodes[s].get("exists", False) for s in graph.predecessors(node))
        out_existing = any(graph.nodes[t].get("exists", False) for t in graph.successors(node))
        if not in_existing and not out_existing:
            orphans.append(node)

    broken = sum(1 for _, t in graph.edges() if not graph.nodes[t].get("exists", False))
    edges = graph.number_of_edges()

    return {
        "total_nodes": n,
        "total_edges": edges,
        "average_out_degree": round(out_deg, 2),
        "orphans": len(orphans),
        "orphan_rate": round(len(orphans) / n, 3),
        "broken_links": broken,
        "broken_link_rate": round(broken / edges, 3) if edges else 0.0,
    }


def read_retrieval_log(state_dir: Path) -> list[dict[str, Any]]:
    """Read all events from the retrieval log JSONL. Skips malformed lines."""
    log_path = Path(state_dir) / "retrieval_log.jsonl"
    if not log_path.exists():
        return []
    events: list[dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _retrieval_breakdown(state_dir: Path, all_titles: list[str]) -> dict[str, Any]:
    events = read_retrieval_log(state_dir)
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    last_7d = 0
    counts: dict[str, int] = {}
    last_seen: dict[str, str] = {}
    for ev in events:
        ts = ev.get("timestamp")
        try:
            t = datetime.fromisoformat(ts) if ts else None
        except ValueError:
            t = None
        if t is not None and t >= cutoff:
            last_7d += 1
        for nid in ev.get("node_ids", []):
            counts[nid] = counts.get(nid, 0) + 1
            if t is not None:
                prev = last_seen.get(nid)
                if prev is None or t.isoformat() > prev:
                    last_seen[nid] = t.isoformat()

    most = sorted(counts.items(), key=lambda x: -x[1])[:10]
    retrieved_set = set(counts.keys())
    never = [t for t in all_titles if t not in retrieved_set]

    return {
        "total_events": len(events),
        "events_last_7d": last_7d,
        "most_retrieved": most,
        "never_retrieved": len(never),
        "never_retrieved_rate": round(len(never) / len(all_titles), 3) if all_titles else 0.0,
        "last_seen": last_seen,
    }


def _compute_warnings(report: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if report["vault"]["total_notes"] > THRESHOLDS["vault_notes"]:
        warnings.append(
            f"Vault has {report['vault']['total_notes']:,} notes "
            f"(above {THRESHOLDS['vault_notes']:,}); consider archival or sharding."
        )
    emb = report["indexes"]["embeddings"]
    if emb["bytes"] > THRESHOLDS["embeddings_bytes"]:
        mb = emb["bytes"] / 1024 / 1024
        warnings.append(
            f"Embeddings index is {mb:.1f} MB "
            f"(above {THRESHOLDS['embeddings_bytes'] / 1024 / 1024:.0f} MB); "
            "consider a smaller model or quantization."
        )
    if report["graph"]["orphan_rate"] > THRESHOLDS["orphan_rate"]:
        warnings.append(
            f"Orphan rate is {report['graph']['orphan_rate']:.1%} "
            f"(above {THRESHOLDS['orphan_rate']:.0%}); many notes aren't graph-connected."
        )
    if report["graph"]["broken_link_rate"] > THRESHOLDS["broken_link_rate"]:
        warnings.append(
            f"Broken link rate is {report['graph']['broken_link_rate']:.1%} "
            f"(above {THRESHOLDS['broken_link_rate']:.0%}); fix wikilink targets."
        )
    nr = report["retrieval"]["never_retrieved_rate"]
    # Only warn about never-retrieved if there's actual retrieval history to compare against.
    if report["retrieval"]["total_events"] > 0 and nr > THRESHOLDS["never_retrieved_rate"]:
        warnings.append(
            f"{nr:.0%} of notes have never been retrieved; consider archival."
        )
    return warnings


def health_report(project_path: Path) -> dict[str, Any]:
    """Compute the full health report dict for a CMA project."""
    project_path = Path(project_path).resolve()
    config = CMAConfig.from_project(project_path).resolve_paths(project_path)
    vault_path = Path(config.vault_path)
    index_root = Path(config.index_path)

    records = parse_vault(vault_path)
    graph = build_graph(records)

    vault_info = _vault_breakdown(vault_path)

    graph_dir = index_root / "graph"
    bm25_dir = index_root / "bm25"
    emb_dir = index_root / "embeddings"
    state_dir = index_root / "state"

    graph_bytes = _dir_size(graph_dir)
    bm25_bytes = _dir_size(bm25_dir)
    emb_bytes = _dir_size(emb_dir)

    embedding_meta: dict[str, Any] = {}
    meta_path = emb_dir / "meta.json"
    if meta_path.exists():
        try:
            embedding_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            embedding_meta = {}

    indexes = {
        "graph": {"bytes": graph_bytes},
        "bm25": {"bytes": bm25_bytes},
        "embeddings": {
            "bytes": emb_bytes,
            "n_docs": embedding_meta.get("n_docs", 0),
            "dim": embedding_meta.get("dim", 0),
            "model": embedding_meta.get("embedder", ""),
        },
        "total_derived_bytes": graph_bytes + bm25_bytes + emb_bytes,
    }

    graph_stats = _graph_breakdown(graph)
    retrieval = _retrieval_breakdown(state_dir, [r.title for r in records])

    report: dict[str, Any] = {
        "vault": vault_info,
        "indexes": indexes,
        "graph": graph_stats,
        "retrieval": retrieval,
    }
    report["warnings"] = _compute_warnings(report)
    return report


def log_retrieval(
    project_path: Path,
    spec_id: str,
    task_id: str,
    query: str,
    fragment_titles: list[str],
    token_estimate: int,
    fragment_count: int,
) -> Path:
    """Append one retrieval event to .cma/state/retrieval_log.jsonl. Returns the log path."""
    project_path = Path(project_path).resolve()
    config = CMAConfig.from_project(project_path).resolve_paths(project_path)
    state_dir = Path(config.index_path) / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / "retrieval_log.jsonl"
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec_id": spec_id,
        "task_id": task_id,
        "query": query,
        "node_ids": fragment_titles,
        "fragment_count": fragment_count,
        "token_estimate": token_estimate,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return log_path

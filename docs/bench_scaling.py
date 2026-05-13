"""Synthetic-vault scaling benchmark for the docs/scaling slide.

Generates realistic-shaped vaults at given sizes, runs `cma index`, then
times retrieve calls (cold + warm). Reports disk footprint and process RAM.

Usage:
    python docs/bench_scaling.py            # runs 1K and 10K
    python docs/bench_scaling.py 1000 10000 100000   # custom sizes

Output is plain text printed to stdout, intended to be pasted into the
build_slideshow.py scale slide table with "(measured)" tags.

Synthetic notes use realistic length, frontmatter, wikilinks to other
notes for graph density, mixed types (decision/pattern/session/etc.).
This exercises the same code paths a real vault would: parsing, BM25
build, embedding compute, graph traversal, fragment extraction.
"""

from __future__ import annotations

import gc
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import psutil

WORDS = (
    "agent memory context retrieval pipeline graph traversal hybrid scoring "
    "decision pattern postmortem session reasoner recorder embedding lexical "
    "vault frontmatter wikilink markdown obsidian fragment chunk paragraph "
    "score depth confidence threshold node ranking architecture system policy "
    "configuration default boost decay relevance signal density store cache "
    "model token query semantic structural relational symbolic compound state "
    "workflow task action observation latency throughput footprint deterministic "
    "inspectable reproducible idempotent stateless cold warm boot startup runtime "
    "module package process thread async queue retry backoff exponential channel "
    "category urgency notification routing fallback override gate human verified "
    "alpha beam width hop edge link backlink outgoing incoming forward reverse "
    "discovery synthesis exclusion supersession archival hygiene curation review"
).split()

NOTE_TYPES = ["decision", "pattern", "session", "postmortem", "note"]
TYPE_FOLDERS = {
    "decision": "003-decisions",
    "pattern": "004-patterns",
    "session": "002-sessions",
    "postmortem": "003-decisions",
    "note": "000-inbox",
}
STATUSES = ["accepted", "proposed", "active", "draft"]


def gen_note(idx: int, total: int, vault: Path, all_titles: list[str]) -> None:
    """Write one synthetic note to the right vault folder."""
    note_type = random.choice(NOTE_TYPES)
    folder = TYPE_FOLDERS[note_type]
    title_words = random.choices(WORDS, k=4)
    title = f"{note_type.capitalize()} {idx:05d} {' '.join(title_words)}"

    # 2-5 wikilinks to other notes for graph density
    if all_titles and len(all_titles) > 1:
        n_links = random.randint(2, min(5, len(all_titles)))
        linked = random.sample([t for t in all_titles if t != title][:200], min(n_links, len(all_titles) - 1))
    else:
        linked = []

    n_paragraphs = random.randint(3, 7)
    paragraphs = []
    for _ in range(n_paragraphs):
        para_len = random.randint(40, 120)
        paragraphs.append(" ".join(random.choices(WORDS, k=para_len)) + ".")
    body = "\n\n".join(paragraphs)
    if linked:
        body += "\n\nRelated: " + ", ".join(f"[[{t}]]" for t in linked)

    safe_title = title.replace(":", "-").replace("/", "-")[:90]
    folder_path = vault / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    note_path = folder_path / f"{safe_title}.md"
    note_path.write_text(
        f"---\n"
        f"type: {note_type}\n"
        f"title: {title}\n"
        f"status: {random.choice(STATUSES)}\n"
        f"confidence: {round(random.uniform(0.4, 0.95), 2)}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    all_titles.append(title)


def gen_vault(project: Path, n_notes: int) -> None:
    """Scaffold a fresh CMA project and populate its vault with N synthetic notes."""
    if project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True)

    # cma init via subprocess
    subprocess.run(
        [sys.executable, "-m", "cma.cli", "init", str(project)],
        check=True, capture_output=True,
    )

    vault = project / "cma" / "vault"
    all_titles: list[str] = []
    for i in range(n_notes):
        gen_note(i, n_notes, vault, all_titles)
        if (i + 1) % 1000 == 0:
            print(f"    generated {i+1}/{n_notes} notes", flush=True)


def dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total / 1_000_000


def file_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    return path.stat().st_size / 1_000_000


def bench_size(n_notes: int) -> dict:
    project = Path(os.environ.get("TEMP", "/tmp")) / f"cma-bench-{n_notes}"
    print(f"\n=== Benchmark: {n_notes:,} notes ===", flush=True)

    # 1. Generate
    t0 = time.perf_counter()
    gen_vault(project, n_notes)
    gen_time = time.perf_counter() - t0
    print(f"  generation: {gen_time:.1f}s", flush=True)

    vault_path = project / "cma" / "vault"
    cache_path = project / "cma" / "cache"
    md_mb = dir_size_mb(vault_path)
    print(f"  markdown on disk: {md_mb:.1f} MB", flush=True)

    # 2. Index (BM25 + embeddings + graph)
    print(f"  running cma index...", flush=True)
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "cma.cli", "index", str(project)],
        capture_output=True, text=True,
    )
    index_time = time.perf_counter() - t0
    print(f"  index time: {index_time:.1f}s", flush=True)
    if proc.returncode != 0:
        print(f"  INDEX FAILED:\n{proc.stderr[-1500:]}", flush=True)
        return {"n_notes": n_notes, "error": "index failed"}

    emb_mb = file_size_mb(cache_path / "embeddings" / "embeddings.npy")
    bm25_mb = file_size_mb(cache_path / "bm25" / "index.pkl")
    print(f"  embeddings on disk: {emb_mb:.1f} MB", flush=True)
    print(f"  BM25 index on disk: {bm25_mb:.1f} MB", flush=True)

    # 3. In-process retrieves (production case: MCP server stays warm; subprocess
    #    cold-start is dominated by the ~10-15s sentence-transformers load and not
    #    representative of what the agent actually experiences in a session).
    queries = [
        "decision about routing and channel mapping",
        "pattern for retry with exponential backoff",
        "postmortem on the api timeout",
        "session that handled confidence thresholds",
        "agent architecture and traversal depth",
        "hybrid scoring and metadata boost",
        "fragment extraction across nodes",
    ]
    print(f"  loading Retriever in-process (one-time model load)...", flush=True)
    proc = psutil.Process()
    gc.collect()
    rss_before_mb = proc.memory_info().rss / 1_000_000
    from cma.retriever import Retriever
    t0 = time.perf_counter()
    retriever = Retriever.from_project(project, embedder="auto")
    cold_load_s = time.perf_counter() - t0
    rss_loaded_mb = proc.memory_info().rss / 1_000_000
    model_load_ms = cold_load_s * 1000
    print(f"  Retriever cold load: {model_load_ms:.0f} ms", flush=True)

    print(f"  running {len(queries)} warm retrieves in-process...", flush=True)
    warm_latencies = []
    for q in queries:
        t0 = time.perf_counter()
        _ = retriever.retrieve(q)
        elapsed = time.perf_counter() - t0
        warm_latencies.append(elapsed)

    # First retrieve after load can still pay an ANN warm-up; report mean of last N-1.
    warm_ms = statistics.mean(warm_latencies[1:]) * 1000 if len(warm_latencies) > 1 else warm_latencies[0] * 1000
    warm_p95_ms = sorted(warm_latencies)[int(len(warm_latencies) * 0.95)] * 1000 if len(warm_latencies) >= 5 else warm_ms
    rss_after_mb = proc.memory_info().rss / 1_000_000
    total_ram_mb = rss_after_mb  # full process RSS
    delta_ram_mb = rss_after_mb - rss_before_mb
    print(f"  warm retrieve mean: {warm_ms:.0f} ms (over {len(warm_latencies)-1} runs)", flush=True)
    print(f"  warm retrieve p95:  {warm_p95_ms:.0f} ms", flush=True)
    print(f"  process RSS after load+retrieve: {total_ram_mb:.0f} MB", flush=True)
    print(f"    of which CMA-added: {delta_ram_mb:.0f} MB", flush=True)

    # Cleanup
    del retriever
    gc.collect()
    shutil.rmtree(project, ignore_errors=True)

    return {
        "n_notes": n_notes,
        "markdown_mb": md_mb,
        "embeddings_mb": emb_mb,
        "bm25_mb": bm25_mb,
        "ram_total_mb": total_ram_mb,
        "ram_delta_mb": delta_ram_mb,
        "index_s": index_time,
        "model_load_ms": model_load_ms,
        "warm_ms": warm_ms,
        "warm_p95_ms": warm_p95_ms,
        "n_warm_samples": len(warm_latencies),
    }


def main() -> None:
    sizes = [int(s) for s in sys.argv[1:]] or [1_000, 10_000]
    random.seed(42)
    results = []
    for n in sizes:
        results.append(bench_size(n))

    # Final summary table
    print("\n\n" + "=" * 95, flush=True)
    print(f"{'NOTES':>8} | {'MD MB':>7} | {'EMB MB':>7} | {'BM25 MB':>8} | "
          f"{'PROC RAM':>9} | {'INDEX s':>8} | {'WARM ms':>8} | {'P95 ms':>7}")
    print("-" * 95)
    for r in results:
        if "error" in r:
            print(f"{r['n_notes']:>8,} | {r['error']}")
            continue
        print(f"{r['n_notes']:>8,} | {r['markdown_mb']:>7.1f} | {r['embeddings_mb']:>7.1f} | "
              f"{r['bm25_mb']:>8.1f} | {r['ram_total_mb']:>9.0f} | {r['index_s']:>8.1f} | "
              f"{r['warm_ms']:>8.0f} | {r['warm_p95_ms']:>7.0f}")
    print("=" * 95, flush=True)
    print("\nNotes:")
    print("  - WARM ms is in-process retrieval (after model load); matches MCP server runtime case")
    print("  - PROC RAM is full process RSS including the ~500 MB sentence-transformers model")
    print("  - Subprocess cold starts (`cma retrieve` from shell) add ~10-15s for model load each call")


if __name__ == "__main__":
    main()

# Scaling benchmark results

Measurements behind the "Designed for single-CPU scale" slide. Reproducible via `python docs/bench_scaling.py`.

## Test setup

- **Hardware**: commodity Windows laptop (single-CPU NumPy, no GPU)
- **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim float32)
- **CMA version**: v0.5
- **Synthetic notes**: 3-7 paragraphs each, 40-120 words per paragraph, 2-5 wikilinks per note, mixed types (decision/pattern/session/postmortem/note)
- **Queries**: 7 representative queries (architecture / retrieval / pattern / postmortem styles); reported figures are the mean and p95 of the last 6 calls (first call warm-up excluded)

## Measured at 1K notes and 10K notes

| Vault size | Markdown | Embeddings | BM25 pickle | Process RAM | Index time | Warm retrieve mean | Warm retrieve p95 |
|---|---|---|---|---|---|---|---|
| 1,000 | 3.7 MB | 1.5 MB | 4.6 MB | 750 MB | 21 s | 42 ms | 56 ms |
| 10,000 | 36.8 MB | 15.4 MB | 46.1 MB | 1.2 GB | 185 s | 173 ms | 246 ms |

## Notes on each column

**Markdown** — synthetic notes are 3-4 KB on average. Real-world decision and pattern notes tend to be larger (5-15 KB) because they include code blocks, tables, and longer rationale. Multiply markdown column by 2-3x for typical production vaults.

**Embeddings** — exact math: 384 dimensions × 4 bytes × N notes. Linear scaling, no surprises. At 1K notes this is 1.5 MB, at 10K it's 15.4 MB (the .4 is metadata).

**BM25 pickle** — heavier per-note than embeddings because the tokenized corpus includes the full token list per document. Roughly 3× the embedding storage at our note sizes.

**Process RAM** — full Python process resident set size after loading the Retriever and running one retrieve. The sentence-transformers model itself is ~500 MB resident regardless of vault size; the rest scales with vault. At 1K notes the model dominates (~700 MB of the 750 MB total). At 10K notes the vault overhead adds ~400 MB.

**Index time** — dominated by the embedding pass (~100-200 documents per second on commodity CPU). At 10K notes this is ~3 minutes one-time cost. Re-indexing is only needed when the vault changes.

**Warm retrieve** — in-process retrieval after the model is loaded into memory. This matches what the MCP server experiences during a live session (one model load at startup, fast queries after). Subprocess invocations (`cma retrieve` from shell) pay the ~10-15s model load on every call and are not representative of agent runtime.

## Projections at 100K and 1M

The slide's 100K row is **linear extrapolation from the measured 10K row**:

- Markdown: 36.8 MB × 10 ≈ 370 MB
- Embeddings: exact (15 MB × 10 = 150 MB)
- Process RAM: ~500 MB (model) + 1.5 GB (vault overhead, linear from 10K) ≈ 2 GB
- Retrieve: 173 ms × 10 ≈ 1.7 s

The retrieve scaling is linear because the dominant cost is one matrix multiplication: query vector (1 × 384) against the embedding matrix (N × 384). NumPy's BLAS-backed `@` operator is O(N) and runs at ~10 GFLOPS on commodity CPUs.

At **1M notes**, linear extrapolation gives ~17 s per query, which is past the threshold where users want a result. That's why the slide notes "needs ANN" at that size — at 1M+ you swap the brute-force NumPy cosine for an approximate nearest neighbor structure (FAISS, hnswlib). The rest of the pipeline (BM25, graph traversal, fragment extraction) continues to scale fine.

## Reproducing

```bash
python docs/bench_scaling.py            # default: 1000 and 10000 notes
python docs/bench_scaling.py 5000 50000 # custom sizes
```

Outputs the measurement table directly. Synthetic vaults are generated into the system temp directory and cleaned up after each run.

## What's NOT measured (yet)

- 100K and 1M actual runs. The 100K row would take ~30 minutes to index; 1M would take hours. Practical to skip until there's a user with a real vault that size who can run the benchmark on their own hardware.
- GPU-accelerated embedding. all-MiniLM-L6-v2 on a modest GPU would index ~10x faster. Out of scope for the "single-CPU" claim.
- Multi-process parallelism. The current code is single-process. Parallelizing index/retrieve across cores is a future enhancement.

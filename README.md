# Contextual Memory Architecture (CMA)

> A local-first, Obsidian-compatible memory layer for persistent AI agents.

CMA is a drop-in memory layer you can add to any agent. Each agent gets its own local Obsidian-compatible vault, a graph-aware retrieval engine, and a structured way to record what it learns - so the next task starts smarter than the last.

**Repository promise: add a persistent contextual memory layer to your agent without rewriting your agent.**

## Why

Most AI agents are stateless. They forget prior decisions, project conventions, what worked, and what failed. Standard RAG helps a little, but agent memory is relational and cumulative - the most useful context isn't the nearest vector chunk, it's a decision linked to a project or a postmortem linked to a failure mode.

CMA reframes memory as three intelligent functions:

- **Reasoner** - frames the goal, decides what context matters
- **Retriever** - converts long-term memory into task-specific context specs (graph + hybrid search)
- **Recorder** - converts completed work into structured, durable memory

The vault is just markdown files with wikilinks. You can open it in Obsidian, version it with git, and grep it from the command line. Indexes are derived and rebuildable - delete `.cma/` and rebuild from the vault any time.

## Status

**v0.2.0 - Phase 1-4 (Skeleton + Storage + Graph + Retrieval).** The Retriever is now functional: hybrid BM25 + (optional) embeddings + multi-hop graph traversal + paragraph-level fragment extraction.

| Phase | Description                                       | Status   |
|-------|---------------------------------------------------|----------|
| 1     | Skeleton, schemas, config, CLI shell              | done     |
| 2     | Markdown vault parser (frontmatter + wikilinks)   | done     |
| 3     | Graph index + health report                       | done     |
| 4     | Hybrid retrieval (BM25 + embeddings + graph)      | done     |
| 5     | Recorder (completion packages, decisions)         | next     |
| 6     | MCP server + adapters (Claude Code, LangGraph)    | planned  |
| 7     | Evaluation harness + benchmarks                   | planned  |

## Install

```bash
git clone <this-repo>
cd contextual-memory-architecture

# Core install (BM25-only retrieval, no embedding deps)
pip install -e .

# Add local embeddings (sentence-transformers, ~500MB with PyTorch)
pip install -e ".[embeddings]"

# Add OpenAI embeddings instead
pip install -e ".[openai]"
```

## Quickstart

```bash
# 1. Initialize a project
cma init my-agent
cd my-agent

# 2. Configure agent integration + embedding provider
cma setup

# 3. Add markdown notes anywhere under vault/, link them with wikilinks

# 4. Train the memory graph (parse, build graph, BM25, embeddings)
cma index

# 5. Inspect graph structure
cma graph health

# 6. Query the memory layer
cma retrieve "what do we know about capital call processing?"
cma retrieve "..." --json --save retriever/specs/CMA-001.json
```

### The training phase

`cma index` is the training phase for your memory graph. It:

1. Parses every markdown note in the vault, extracts frontmatter, follows wikilinks
2. Builds a directed graph keyed by note (NetworkX)
3. Builds a BM25 lexical index over titles and bodies
4. Computes embeddings (if a provider is configured) for semantic search

Outputs land in `.cma/`:
- `.cma/graph/nodes.json` - node manifest
- `.cma/bm25/index.pkl` - tokenized corpus
- `.cma/embeddings/embeddings.npy` - vector matrix
- `.cma/embeddings/doc_ids.json` - row-to-record mapping
- `.cma/embeddings/meta.json` - provider/model/dimension

Re-running is cheap and idempotent. The whole `.cma/` directory is rebuildable from the markdown vault.

### Connecting your agent

`cma setup` walks you through connecting CMA to your agent. The three options:

1. **Claude Code (MCP)** - the recommended path for most users. Phase 6 will ship an MCP server you register in your Claude Code config; for now it prints the snippet you'll paste once Phase 6 lands.
2. **Python SDK** - import `cma` directly in your agent code. See [Python API](#python-api).
3. **Generic CLI** - shell out to `cma retrieve` from any agent framework.

The setup command also configures your embedding provider:
- `sentence-transformers` (local, default, no API key) - install with `pip install '.[embeddings]'`
- `openai` (cloud) - install with `pip install '.[openai]'`, set `OPENAI_API_KEY`
- `none` - BM25 lexical search only

## Project Layout

```
my-agent/
  cma.config.yaml        # vault path, retrieval defaults, recorder policy
  vault/                 # canonical memory (Obsidian-compatible markdown)
    000-inbox/
    001-projects/
    002-sessions/
    003-decisions/
    004-patterns/
    ...
  reasoner/              # task frames, prompts, policies
  retriever/             # context specs, graph reports
  recorder/              # completion packages, write logs
  .cma/                  # derived indexes (rebuildable)
    graph/
    bm25/
    embeddings/
```

## Concepts

- **Memory** is durable stored experience: markdown notes in the vault.
- **Context** is the temporary working set built for a specific task.
- **Context spec** is a structured artifact - retrieved fragments, relationship map, provenance, scores. Inspectable, debuggable, testable.
- **Memory graph** is built from wikilinks; nodes carry frontmatter as metadata.

The Retriever pipeline:

```
hybrid seed search (BM25 + embeddings)
  -> beam-pruned graph traversal (max_depth, beam_width)
  -> per-node hybrid + metadata-boost + depth-decay scoring
  -> paragraph-level fragment extraction
  -> cross-node fragment deduplication
  -> ContextSpec
```

The full whitepaper lives in `WHITEPAPER.md` (coming soon).

## Python API

```python
from cma import Retriever, render_markdown

retriever = Retriever.from_project("./my-agent")
spec = retriever.retrieve(
    "what do we know about capital call processing?",
    max_depth=2,
    beam_width=5,
)

# Use the structured form
for frag in spec.fragments:
    print(frag.source_node, frag.node_score, frag.text[:100])

# Or render as inspectable markdown to commit to vault/008-context-specs/
print(render_markdown(spec))
```

## Design principles

- **Local-first.** No server, no cloud (unless you opt into OpenAI embeddings). The vault is yours.
- **Inspectable.** Memory is markdown. Open it in Obsidian, grep it, version it.
- **Framework-agnostic.** CLI, Python SDK, and (Phase 6) MCP. Bring your own agent.
- **Per-agent memory.** Each agent gets its own vault. No shared global brain.
- **Rebuildable indexes.** `.cma/` is derived state. Canonical truth is markdown.
- **Pluggable embeddings.** Default is local sentence-transformers; OpenAI is a one-line config swap; or implement the `Embedder` protocol for your own.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT

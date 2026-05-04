# Contextual Memory Architecture (CMA)

> A lightweight memory layer each agent carries with it. Local-first, Obsidian-compatible, fractal-by-design.

CMA is a memory architecture small enough to live next to a single agent. Each agent gets its own Obsidian-compatible vault, a graph-aware retrieval engine, and a structured way to record what it learns - so the next task starts smarter than the last. No shared cloud brain, no central server, no cross-agent contamination by default.

**Repository promise: add a persistent contextual memory layer to your agent without rewriting your agent.**

## Why

Most AI agents are stateless. They forget prior decisions, project conventions, what worked, and what failed. Standard RAG helps a little, but agent memory is relational and cumulative - the most useful context isn't the nearest vector chunk, it's a decision linked to a project or a postmortem linked to a failure mode.

CMA reframes memory as three intelligent functions:

- **Reasoner** - frames the goal, decides what context matters
- **Retriever** - converts long-term memory into task-specific context specs (graph + hybrid search)
- **Recorder** - converts completed work into structured, durable memory

The vault is just markdown files with wikilinks. You can open it in Obsidian, version it with git, and grep it from the command line. Indexes are derived and rebuildable - delete `.cma/` and rebuild from the vault any time.

## Lightweight, per-agent, fractal-by-design

CMA is meant to be the memory layer a single agent **carries with it** - small enough that every agent in a system can have its own.

- **Per-agent vaults are the unit.** An agent's vault holds its own decisions, sessions, patterns, and project context. Two agents working in the same system don't pollute each other's memory; their experiences stay separate unless explicitly shared.
- **The architecture is fractal.** A vault is a graph of notes. Nothing stops a vault itself from becoming a single node in a larger graph - a system-level or network-level memory graph that links agents instead of notes. The same primitives (graph traversal, hybrid search, fragment extraction, context spec assembly) apply at any scale.
- **What that unlocks (future direction).** Multi-agent systems where the Retriever traverses across agent boundaries when context demands it. Cross-agent provenance. Network-wide pattern recognition. Selective memory federation - one agent loaning a slice of its graph to another for the duration of a task. CMA v0.3 is the per-agent foundation; the fractal layer is on the roadmap.

The local-first, markdown-as-canonical design exists precisely so this composes cleanly: a vault is a portable artifact, an MCP server is a portable interface, and a graph of vaults is just another graph.

## Status

**v0.3.0 - Phases 1-7 functional.** All seven phases of the whitepaper are wired up. Retrieval, recording, MCP server, and an eval harness for the four-mode comparison are in place.

| Phase | Description                                       | Status   |
|-------|---------------------------------------------------|----------|
| 1     | Skeleton, schemas, config, CLI shell              | done     |
| 2     | Markdown vault parser (frontmatter + wikilinks)   | done     |
| 3     | Graph index + health report                       | done     |
| 4     | Hybrid retrieval (BM25 + embeddings + graph)      | done     |
| 5     | Recorder (sessions, decisions, patterns, daily)   | done     |
| 6     | MCP server (10 tools, stdio transport)            | done     |
| 7     | Evaluation harness (Modes A/B/C/D, retrieval metrics) | done |

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

# Add MCP server support (for Claude Code integration)
pip install -e ".[mcp]"

# Everything
pip install -e ".[all]"
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

# 7. Record what an agent learned
cma record path/to/completion_package.yaml

# 8. Run a benchmark suite
cma evals run examples/benchmark.yaml --mode graphrag

# 9. Serve over MCP for Claude Code
cma mcp serve --project .
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

1. **Claude Code (MCP)** - the recommended path for most users. Register the CMA MCP server in your Claude Code config; the agent calls retrieve/record/graph tools directly during a session. See [MCP server](#mcp-server) below.
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
from cma import Recorder, Retriever, render_markdown
from cma.schemas import CompletionPackage, Decision

# Retrieval
retriever = Retriever.from_project("./my-agent")
spec = retriever.retrieve(
    "what do we know about capital call processing?",
    max_depth=2,
    beam_width=5,
)
for frag in spec.fragments:
    print(frag.source_node, frag.node_score, frag.text[:100])
print(render_markdown(spec))  # inspectable markdown form

# Recording
recorder = Recorder.from_project("./my-agent")
package = CompletionPackage(
    task_id="CMA-2026-0001",
    goal="Diagnose slow processing",
    summary="Synchronous fund-admin API in hot path",
    decisions=[Decision(
        title="Move to async queue",
        status="accepted",
        confidence=0.86,
        rationale="Queue isolates external API latency from request path",
    )],
)
result = recorder.record_completion(package)
print(result.summary())
```

## MCP server

CMA exposes ten tools over MCP for any agent that speaks the protocol (Claude Code, the Anthropic SDK, etc.):

**Graph primitives** (composable, fine-grained):
- `search_notes` - hybrid search returning top-k matches
- `get_note` - fetch full note content
- `get_outgoing_links` / `get_backlinks` - follow wikilinks
- `traverse_graph` - notes within N hops
- `search_by_frontmatter` - filter by YAML metadata

**Higher-level orchestrators** (one-shot):
- `retrieve` - full Retriever pipeline returning a markdown Context Spec
- `record_completion` - Recorder ingestion
- `graph_health` - graph health report
- `reindex` - refresh the in-memory index after vault changes

To wire into Claude Code, add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "cma": {
      "command": "cma",
      "args": ["mcp", "serve", "--project", "/absolute/path/to/your/cma-project"]
    }
  }
}
```

## Design principles

- **Lightweight.** Small enough to live next to a single agent; pure-Python core, no daemons, no schema migrations.
- **Per-agent memory.** Each agent gets its own vault. No shared global brain by default.
- **Fractal-ready.** A vault is a graph of notes; a graph of vaults is just another graph. Same primitives compose upward.
- **Local-first.** No server, no cloud (unless you opt into OpenAI embeddings). The vault is yours.
- **Inspectable.** Memory is markdown. Open it in Obsidian, grep it, version it.
- **Framework-agnostic.** CLI, Python SDK, MCP. Bring your own agent.
- **Rebuildable indexes.** `.cma/` is derived state. Canonical truth is markdown.
- **Pluggable embeddings.** Default is local sentence-transformers; OpenAI is a one-line config swap; or implement the `Embedder` protocol for your own.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT

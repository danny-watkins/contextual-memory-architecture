# Contextual Memory Architecture (CMA)

> A memory layer your agent carries with it. Local-first, Obsidian-compatible, fractal-by-design.

**Status: v0.5 alpha · under active development**

Architecture is settled (see [whitepaper](docs/CMA_Whitepaper_v0.5.pdf)). The full pipeline — hybrid retrieval, graph traversal, fragment extraction, Context Spec assembly, persisted memory, auto-firing hooks, and a live verification dashboard — works end-to-end on the included [email-checker demo](examples/email-checker/). 190 tests pass. Not yet battle-tested across diverse agent shapes, large vaults, or many users. Looking for collaborators and early adopters to season it.

[Whitepaper (PDF)](docs/CMA_Whitepaper_v0.5.pdf) · [Slideshow (PDF)](docs/CMA_Slideshow_v0.5.pdf) · [Demo agent](examples/email-checker/) · [Session log](SESSION_LOG.md)

---

## What it does

Most AI agents are stateless. They forget prior decisions, project conventions, what worked, what failed. Standard RAG helps a little, but agent memory is **relational and cumulative** — the most useful context is not the nearest vector chunk, it's the decision linked to a project or the postmortem linked to a failure mode.

CMA gives any agent a persistent memory layer it carries through every session:

- **Reasoner** — your agent. Frames the goal, decides what context matters.
- **Retriever** — converts long-term memory into task-specific Context Specs via hybrid scoring (BM25 + embeddings) + graph traversal + paragraph-level fragment extraction.
- **Recorder** — converts completed work into structured durable memory under a confidence-gated write policy.

The vault is plain markdown with `[[wikilinks]]`. Open it in Obsidian. Version it with git. Grep it from the shell. Derived indexes live in `cma/cache/` and are rebuildable from the vault at any time.

## Install

```bash
git clone https://github.com/danny-watkins/contextual-memory-architecture.git
cd contextual-memory-architecture
pip install -e ".[all]"
```

Optional dependency groups: `[embeddings]` (sentence-transformers for hybrid retrieval), `[openai]` (OpenAI embeddings), `[mcp]` (MCP server for Claude Code).

## Quickstart — one command

```bash
cd /path/to/your-agent-project
cma add
```

`cma add` is the single command that wires CMA into any agent project. It:

1. Scaffolds `cma/` (vault, config, cache, memory_log) under your project root
2. Copies the bundled Obsidian graph config so the visualization works on first open
3. Ingests your project's source files into `cma/vault/020-sources/`
4. Builds the BM25 index + embeddings + graph state
5. Writes `CLAUDE.md` (with the CMA prompt block between markers), `.claude/agents/cma-*.md` (four pre-built sub-agents), and `.claude/settings.json` (auto-firing hooks)
6. Registers the CMA MCP server in `.mcp.json`

After `cma add`, **restart Claude Code in the project directory** so the project-scope MCP server and hooks load.

Then open these in parallel as you work:

- The agent in Claude Code — runs as usual; memory is auto-loaded before every prompt and auto-captured at session end
- The memory log dashboard at `cma/memory_log/dashboard.html` — auto-refreshing every 5 seconds, every search/retrieve/record event with clickable artifact links
- The Obsidian graph view on `cma/vault/` — see the memory structure visually; new Context Specs appear as red nodes

## How auto-firing works

CMA registers two hooks with Claude Code (project-scope `.claude/settings.json`):

- **`UserPromptSubmit` → `cma hook user-prompt`** runs the full Retriever pipeline on every prompt and injects the rendered Context Spec as pre-turn context. The agent always starts with relevant memory loaded; it doesn't need to remember to ask for it.
- **`Stop` → `cma hook stop`** captures a session summary to `cma/vault/002-sessions/`.

Per-hook cost is ~2-3 seconds (loading the embedding model into a fresh Python process). Falls inside the agent's normal first-token latency.

For deeper retrievals or deliberate writes, the agent still uses MCP tools (`mcp__cma__retrieve`, `mcp__cma__record_completion`, etc.) or invokes one of the bundled sub-agents (`cma-retriever`, `cma-recorder`, `cma-curator`, `cma-bootstrap`).

## Project layout after `cma add`

```
your-agent/
  CLAUDE.md              # your agent's instructions (CMA block merged between markers)
  .claude/agents/        # four CMA sub-agents
  .claude/settings.json  # CMA hooks registered
  .mcp.json              # CMA MCP server registered
  cma/
    config.yaml
    vault/               # canonical markdown memory + .obsidian/ config bundled
      000-inbox/ ... 020-sources/
    cache/               # BM25, embeddings, graph state (derived from vault)
    memory_log/
      activity.jsonl     # append-only event stream
      dashboard.html     # live visual viewer
      write_logs/  proposals/
```

Three top-level subdirectories under `cma/`: `vault/` (canonical), `cache/` (derived), `memory_log/` (operational). The three Claude Code files at the project root are required by the host runtime.

## CLI reference

| Command | Purpose |
|---------|---------|
| `cma add [path] [--user]` | One-shot install: scaffold + wire prompt, sub-agents, MCP, hooks |
| `cma init <path>` | Scaffold only (vault + config). Used internally by `cma add` |
| `cma init-claude` | Write a global CMA hint into `~/.claude/CLAUDE.md` so any session can install via "add CMA" |
| `cma setup [path]` | Interactive: integration + embedding provider |
| `cma index [path] [--no-embeddings]` | Rebuild BM25, embeddings, graph from the vault |
| `cma ingest-folder <src> --project <p>` | Pull external source files into the vault |
| `cma retrieve "<query>"` | Run the Retriever, emit a Context Spec |
| `cma record <package.yaml>` | Recorder ingestion (confidence-gated writes) |
| `cma mcp serve --project <p>` | Start MCP server over stdio |
| `cma activity [--watch]` | Tail the memory log in the terminal |
| `cma health [--json]` | Vault stats + retrieval activity |
| `cma archive --type T --older-than D` | Archive cold notes |
| `cma supersede "Old" --by "New"` | Mark decision superseded |
| `cma graph health [path]` | Graph structure report |
| `cma evals run <bench.yaml>` | Run benchmark suite |
| `cma version` | Print installed version |

## MCP tools available to the agent

Six graph primitives and four orchestrators, exposed over stdio:

- `search_notes(query, top_k)` — hybrid lexical + semantic search
- `get_note(title)` — fetch a single note's body, frontmatter, and links
- `get_outgoing_links(title)` / `get_backlinks(title)` — neighborhood navigation
- `traverse_graph(start, depth)` — BFS within N hops
- `search_by_frontmatter(key, value)` — metadata filter
- `retrieve(query, max_depth, beam_width)` — full Retriever pipeline, returns rendered Context Spec
- `record_completion(yaml_str, dry_run)` — write decisions/patterns/sessions under the confidence-gated policy
- `graph_health()` — structural report
- `reindex()` — rebuild in-memory state after vault changes

## What's in the bundled demo

`examples/email-checker/` is a small Python agent project (a Gmail triage agent stub) that exists to exercise CMA end-to-end. It has its own `CLAUDE.md`, `agent.py`, `skills/`, `prompts/`, `docs/decisions/`, etc. — the kind of structure a real agent project might have. Run `cma add` inside it and you have a working memory layer + dashboard + Obsidian graph view in one minute.

## Concepts

- **Memory** is durable stored experience: markdown notes in the vault.
- **Context** is the temporary working set built for a specific task.
- **Context Spec** is a structured artifact (`vault/008-context-specs/spec-XXXXXXXX.md`) — retrieved fragments, relationship map, provenance, scores. Inspectable, debuggable, citable in `[[wikilink]]` form.
- **Fragment** is a single paragraph (or short section) of text the Retriever decided was relevant. The Retriever cherry-picks paragraphs — it does not paste whole notes into the spec.
- **The GraphRAG flywheel**: every Retriever fire persists a new spec note. Future retrieves can find prior specs as relevant sources. Memory compounds across turns.

## Honest about where this is

**What works:**
- Hybrid retrieval, graph traversal, fragment extraction, Context Spec assembly
- Auto-firing hooks (Claude Code)
- Confidence-gated recorder (decisions, patterns, sessions, daily logs)
- Auto-related linking between decisions/patterns (BM25 lookup at write time)
- Inbox prompt capture + curator promotion
- Live memory log dashboard (static HTML, no server)
- Obsidian graph visualization with bundled color groups
- Bundled MCP server + four sub-agents
- 190 tests across the engine

**What's not done:**
- Fragment-level scoring is still BM25-only (node-level hybrid scoring works; fragment-level embedding pending)
- Not benchmarked at scale — only validated on the demo project and small vaults. The 100K-note scaling numbers in the slideshow are projections from algorithmic complexity, not measurements.
- MCP server events sit in their own session block in the dashboard (separate from Claude Code session block) because there's no shared session_id channel
- The `cma-curator` sub-agent's noise-promotion mechanism is defined but not yet automated
- No PyPI release yet — install from source via `pip install -e .`

See [SESSION_LOG.md](SESSION_LOG.md) for the full state-of-build, open threads, and where to start contributing.

## Lightweight, per-agent, fractal-by-design

CMA is meant to be the memory layer a single agent **carries with it** — small enough that every agent in a system can have its own.

- **Per-agent vaults are the unit.** Two agents working in the same system don't pollute each other's memory.
- **Fractal architecture.** A vault is a graph of notes. Nothing stops a vault itself from becoming a single node in a larger graph — a network-level memory graph that links agents. The same primitives apply at any scale. Future direction (see whitepaper §7.2).

## Contributing

Early stage. Open an issue before a large PR so we can shape direction together. The [SESSION_LOG.md](SESSION_LOG.md) lists current open threads ranked by payoff. Smaller items: typos, doc fixes, additional test coverage — feel free to PR directly.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) — Copyright (c) 2026 Danny Watkins.

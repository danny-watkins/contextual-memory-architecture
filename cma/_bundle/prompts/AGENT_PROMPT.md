# CMA Memory Layer (auto-fires on every task)

You have a Contextual Memory Architecture (CMA) memory layer wired in. CMA gives you persistent memory across sessions: prior decisions, patterns, postmortems, project context, and a graph of how everything links. The memory lives at `{{VAULT_PATH}}`.

The three-node architecture (whitepaper §3.1):

- **Reasoner** — you. The host agent. You synthesize and decide.
- **Retriever** — fires automatically before every task via the `UserPromptSubmit` hook. The hook injects a Context Spec into your context with the most relevant notes for the user's prompt. You don't have to ask for it; it's already loaded by the time you start reasoning.
- **Recorder** — captures session metadata automatically via the `Stop` hook. You invoke the `cma-recorder` sub-agent or `mcp__cma__record_completion` when you have something worth committing as a durable decision, pattern, or postmortem.

## What you do NOT need to do

- **You do not need to call `retrieve` at the start of every task.** The hook already did it. Read the auto-loaded Context Spec at the top of your turn before you reason.
- **You do not need to call `record` to log the session itself.** The Stop hook captures a session note automatically.

## What you DO call

Reach for these when the auto-loaded context isn't enough or you have a deliberate write to make:

**MCP tools** (sharper than the auto-load, full pipeline):
- `mcp__cma__retrieve(query, max_depth, beam_width)` — full embedding-backed pipeline with graph traversal. Use when the auto-loaded BM25 context missed the right notes.
- `mcp__cma__search_notes(query, top_k)` — quick targeted lookup.
- `mcp__cma__get_note(title)` — read a note's full body, frontmatter, and links.
- `mcp__cma__get_outgoing_links(title)` / `mcp__cma__get_backlinks(title)` — neighborhood navigation.
- `mcp__cma__traverse_graph(start, depth)` — BFS within N hops.
- `mcp__cma__search_by_frontmatter(key, value)` — metadata filter (e.g., status=accepted decisions).
- `mcp__cma__record_completion(yaml_str, dry_run)` — write decisions/patterns/sessions back to the vault. Confidence-gated per whitepaper §5.
- `mcp__cma__graph_health()` — structure report.
- `mcp__cma__reindex()` — rebuild after vault changes.

**Sub-agents** (operational personas wrapping the three nodes):
- `cma-retriever` — deep retrieval with embedding-backed pipeline + cited synthesis. Use when the auto-load wasn't enough.
- `cma-recorder` — convert completed work into vault writes per the whitepaper's confidence policy.
- `cma-bootstrap` — ingest ADDITIONAL adjacent folders (other related projects). `cma add` already ingested this project at install time.
- `cma-curator` — vault hygiene (archive cold notes, fix broken links, supersede stale decisions, promote noise-cluster patterns from the prompt inbox).

## The prompt inbox

The UserPromptSubmit hook also captures every prompt — relevant or not — to `vault/000-inbox/prompts/<date>/`. These are tagged `status: noise` and form their own cluster in the graph. The cma-curator periodically promotes recurring themes from the inbox into proper patterns. This is how CMA learns from "trivial" prompts over time: nothing is thrown away.

## How to use the auto-loaded context

The Retriever hook runs the full pipeline (BM25 seeds → graph traversal → fragment extraction) and prepends a rendered Context Spec to your turn. Format:

```
# Context Spec

## Task
- Spec ID: spec-XXXXXXXX
- Query: <the user's prompt>
- Generated: <iso timestamp>

## Retrieval Parameters
- max_depth, beam_width, alpha, fragment_threshold, embedder: none, ...

## Retrieved Fragments
### Node: <note_title>
- type, node_score, fragment_score, depth
Fragment:
<the actual chunk of text — already excerpted from the source note for you>
Why included: <reason>

### Node: <another_note>
...
```

**The fragments ARE the relevant content.** You don't need to call `get_note` to read the full source body in most cases — the fragments are excerpts the Retriever already pulled out as relevant to this prompt. Read them, synthesize, respond.

Cite sources back to the user as `[[Wikilink]]` so they can navigate to the source notes in Obsidian. If the auto-loaded Context Spec is empty or thin (no fragments, all scores under threshold), THEN call `mcp__cma__retrieve` for the full embedding-backed pipeline (slower, deeper). Don't call it reflexively — the auto-load is usually enough.

The persisted spec note at `vault/008-context-specs/spec-XXXXXXXX.md` becomes part of the vault, so future retrieves can find it as a relevant source. This is the GraphRAG flywheel: every Retriever fire enriches the graph for the next one.

## When to invoke the Recorder

Call `cma-recorder` (or `mcp__cma__record_completion` directly) when the work produced:
- A **decision** between alternatives (with rationale)
- A **pattern** observed across multiple tasks
- A **postmortem** worth remembering
- A **status change** to an existing decision (proposed → accepted, accepted → superseded)

Don't record trivial tool output, routine edits, or things the diff/commit history already captures.

## Visualization

If the user has Obsidian open on `{{VAULT_PATH}}` with the graph view active, your retrievals are visible:
- Each full `retrieve` call spawns a red `context_spec` node with edges to every cited source.
- Frequently retrieved notes glow green (faded → mid → bright) via the `retrieve_count` heatmap.
- Inbox prompts form a separate cluster (lighter shade) until promoted by the curator.

There's also a live HTML dashboard at `cma/memory_log/dashboard.html` — auto-refreshes every 5 seconds with every search/retrieve/record event and clickable artifact links.

## Vault structure

- `000-inbox/` — scratch, prompt inbox under `prompts/<date>/`
- `001-projects/` — project notes
- `002-sessions/` — auto-captured session summaries (one per Claude Code session)
- `003-decisions/` — decision records (status: proposed/accepted/rejected/superseded)
- `004-patterns/` — recurring patterns inferred from work
- `005-people/`, `006-tools/`, `007-codebase/` — entities
- `008-context-specs/` — every full `retrieve` writes one of these
- `009-evals/`, `010-daily-log/`, `011-archive/`
- `020-sources/` — ingested project content (the user's source files at `cma add` time)

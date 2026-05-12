# Email Checker — CMA Demo Agent

A small stand-in agent project we use to exercise CMA end-to-end. Not production code. The structure here is roughly what a real agent project might look like before CMA is installed: a `CLAUDE.md` instructing the agent, some Python in `skills/`, prompts as markdown in `prompts/`, design docs and decision records in `docs/`, runtime config in `config/`.

## Try CMA on this demo

From the repo root, after `pip install -e ".[all]"`:

```bash
cd examples/email-checker
cma add
```

That single command:

1. Scaffolds `cma/` next to the existing agent files (`vault/`, `cache/`, `memory_log/`)
2. Ingests the project's source files into `cma/vault/020-sources/`
3. Builds the BM25 index + embeddings + graph
4. Writes/merges `CLAUDE.md` (CMA block appended between markers), copies the four CMA sub-agents, registers the MCP server, and installs the auto-firing hooks

After `cma add` completes, restart Claude Code in this directory so the project-scope MCP server and hooks load. Then any prompt you send to the agent has memory loaded into context automatically.

## What to try first

Open the dashboard side-by-side with Claude Code:

```
file:///<full-path>/examples/email-checker/cma/memory_log/dashboard.html
```

Then try prompts like:

- "what does notify.py do"
- "explain the tradeoff between Gmail API and IMAP for this agent's email fetching"
- "summarize how the agent handles low-confidence classifications"

Each prompt will appear in the dashboard within ~5 seconds, with per-source token breakdowns and clickable `view fragments` links opening the persisted spec.

If you also have Obsidian installed, open `examples/email-checker/cma/vault/` as an Obsidian vault and turn on the graph view (Ctrl+G). Every retrieve will spawn a new red `context_spec` node connected to its source nodes — you can watch the memory graph grow.

## What this demo is NOT

- Real working email-checker code. It's stubs, types, and design docs that exist to give CMA realistic content to index and retrieve over.
- A complete agent template. For a real project, you'd flesh out the stub functions in `skills/`, fill `config/settings.yaml`, and wire the LLM provider you want.

The point of the demo is to exercise CMA's pipeline against a realistic-looking agent project, not to be a usable email triage tool.

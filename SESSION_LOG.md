# CMA Session Log

A running log of where we are in the build, so a cold-start return to this project takes minutes instead of hours.

Last updated: 2026-05-12

---

## Where we are right now

CMA is a working drop-in memory layer that auto-fires on every Claude Code task, runs the full Retriever pipeline (hybrid BM25+embeddings, graph traversal, fragment extraction, spec persistence), captures the prompt + session, and exposes everything through a live HTML dashboard. End-to-end loop is functional on the email-checker demo.

**Source of truth:** `docs/CMA_Whitepaper_v0.5.pdf` (built from `docs/build_whitepaper.py`).

**Reference install:** `C:\Users\danny\OneDrive\Desktop\email-checker\` — a stand-in agent project where we exercise CMA end-to-end.

**Status:** all 190 tests pass. Architecture matches the whitepaper. Both the auto-fire hook AND the MCP tools are wired and producing real Context Specs with extracted fragments.

---

## Architecture, in one breath

```
Reasoner (the host agent) <-- hooks at task boundaries -->  Retriever / Recorder
                                       |
                                       v
                   cma/ (vault, cache, memory_log inside each agent project)
```

Three folders inside `cma/` in any installed agent project:

- `vault/` — canonical markdown memory (Obsidian-compatible, .obsidian/ config bundled)
- `cache/` — derived BM25/embeddings/graph state, regenerable via `cma index`
- `memory_log/` — operational stream: `activity.jsonl` (truth), `dashboard.html` (live viewer auto-refreshing every 5s), `write_logs/`, `proposals/`

Three Claude Code-required files at the agent's project root:

- `CLAUDE.md` (with CMA prompt block between markers, merged into agent's existing CLAUDE.md)
- `.claude/agents/cma-*.md` (4 sub-agents: bootstrap, retriever, recorder, curator)
- `.mcp.json` + `.claude/settings.json` (MCP server + auto-fire hooks)

---

## What's wired and working

- **One-shot install**: `cma add` from any directory scaffolds the vault, ingests the user's project files, builds the index (BM25 + embeddings), copies bundled agents/prompts/Obsidian config, registers MCP server + Claude Code hooks. Idempotent.
- **Auto-firing hooks** (Claude Code project-scope `.claude/settings.json`):
  - `UserPromptSubmit` → `cma hook user-prompt` runs full hybrid Retriever, persists spec, injects rendered Context Spec into agent context, captures prompt to inbox bucket
  - `Stop` → `cma hook stop` appends session summary to `vault/002-sessions/<session-id>.md`
- **Session ID grouping**: events from hooks group under Claude Code's `session_id` so the dashboard shows one block per conversation
- **Per-source token accounting**: every retrieve event logs each source's `tokens_extracted / tokens_total / percent / fragments` to activity.jsonl; the dashboard renders this inline and provides a "view fragments" link to the spec.md
- **Auto-related linking**: Recorder writes `## Related` sections via BM25 lookup over existing decisions/patterns (whitepaper §5.6)
- **Confidence-gated writes**: §5.1–5.5 policy implemented; decision/pattern/session/daily-log writes work end-to-end via `cma-recorder` sub-agent and `mcp__cma__record_completion`
- **Inbox prompt bucket**: every prompt captured to `vault/000-inbox/prompts/<date>/` with `status: noise` (whitepaper §5.8)
- **Memory log dashboard**: self-contained HTML at `cma/memory_log/dashboard.html`, meta-refresh every 5s, sessions sorted by recent activity, color-coded events, filter bar, clickable source links + view-fragments links
- **Robust vault parsing**: malformed YAML in one note degrades that note gracefully without crashing the load (whitepaper §6.3)
- **Boilerplate fragment filter**: markdown headings, ingest attribution lines, and lone code fences excluded from fragment selection (whitepaper §4.4)

---

## Test coverage

190 tests in `tests/`. Major suites:

- `test_activity.py` — activity log writer, dashboard renderer, session-id override
- `test_hooks.py` — UserPromptSubmit / Stop hook entry points, prompt-inbox capture, quick_retrieve full pipeline + filter behavior
- `test_per_source_tokens.py` — per-source token math, spec_path threading, sorting
- `test_retriever.py` — full pipeline, hybrid scoring, traversal, fragments
- `test_recorder.py` — confidence policy, write/draft/propose routing, auto-related links
- `test_fragments.py` — paragraph scoring, boilerplate filter
- `test_cli.py` — `cma init`, `cma add`, `cma ingest-folder`, `cma index`, `cma retrieve`, `cma activity`
- `test_mcp.py` — MCP server tools, lazy init
- `test_health.py`, `test_lifecycle.py`, `test_evals.py` — health metrics, archive/supersede, eval harness

---

## Where the email-checker demo stands

`email-checker/` has:
- Agent files: `agent.py`, `skills/{classify,fetch_emails,notify,summarize}.py`, `prompts/{system,classify_email,summarize_thread}.md`, `docs/{architecture,api_notes,classification_taxonomy}.md`, `docs/decisions/{use_gmail_api,classification_thresholds,notification_channels}.md`, `config/settings.yaml`
- `CLAUDE.md` (agent's own intro + appended CMA prompt block between markers)
- `.claude/agents/email-checker.md` (dev assistant for the agent itself)
- `.claude/agents/cma-{bootstrap,retriever,recorder,curator}.md` (the four CMA sub-agents)
- `.claude/settings.json` (hooks registered)
- `.mcp.json` (MCP server)
- `cma/` with vault populated (~20 source notes ingested), several context_specs from prior tests, session notes from prior hook runs

Latest successful end-to-end verification: prompt "what does notify.py do" → hybrid retrieval → 10 sources, 1038 tokens extracted, real notify.py code as top source, dashboard shows everything with view-fragments links working.

---

## Open threads / known imperfections

1. **Fragment-level scoring is still BM25-only.** Embedding contribution is at the NODE selection level. The fragment selection within a chosen note still uses lexical overlap. Result: occasionally a less-content-rich paragraph from a relevant note gets picked over the substantive paragraph. Fix would be to embed each paragraph too and use hybrid at the fragment level. Not done yet.

2. **Dashboard source ordering.** Sources are listed by `tokens_extracted` descending, which can put a high-volume but less-relevant source above a lower-volume but more relevant one. Two display options proposed (sort by node_score, or show node_score alongside tokens). Not landed yet.

3. **Per-hook embedding model load is ~2-3 seconds.** Hidden inside agent's normal response latency, so not a UX issue today. If it becomes one, the proper next step is a small `cma daemon` long-running process that keeps the model warm and exposes a local IPC endpoint the hook talks to.

4. **MCP server events sit in their own session block in the dashboard**, separate from the Claude Code session block, because the MCP server doesn't receive the Claude Code session_id over stdio. Cosmetic, not functional. Fix would be a tiny shared file the hook writes and the MCP server reads on each tool call.

5. **Cross-vault flywheel hygiene.** The vault now has multiple context_spec notes per session. Spec exclusion in the auto-fire hook prevents these from dominating retrieval, but the spec count grows linearly with prompt count. The `cma-curator` is designed to prune low-value specs over time, but no automated curator run is scheduled — manual invocation only.

6. **Source code ingestion adds "From [[project]] / path/file.py" attribution lines.** The boilerplate filter handles this at fragment-selection time, but ideally `cma ingest-folder` would not produce those lines in the first place. The attribution is in `cma/ingest.py:_render_source_note`. Cleaning up the ingest output (removing the attribution paragraph, keeping the wikilink metadata in frontmatter only) is a separate change.

7. **Debug breadcrumbs in `cma/hooks.py`** are still active (`_debug_log` calls in user_prompt_hook and _quick_retrieve). They write to `cma/memory_log/hook_debug.log` on every fire. Useful while debugging; should be gated behind a flag or removed before any release.

8. **`cma activity` CLI** exists but hasn't been live-tested with `--watch`, `--type`, `--session` filters at any volume. Worth a smoke test before any users encounter it.

---

## Where to start next session

If you come back fresh and want to continue:

1. Read this file + `docs/CMA_Whitepaper_v0.5.pdf` (just §5.7-5.9 for the recent additions)
2. Decide which thread from "Open threads" to pull:
   - Cleanest payoff: thread #6 (clean up ingest attribution at source) — improves all future retrievals
   - Most useful UX polish: thread #2 (dashboard source ordering)
   - Most demanding: thread #1 (fragment-level hybrid scoring) — a real architectural enhancement
3. The email-checker demo is at `C:\Users\danny\OneDrive\Desktop\email-checker\` and ready for further test prompts
4. Dashboard: `file:///C:/Users/danny/OneDrive/Desktop/email-checker/cma/memory_log/dashboard.html`

---

## File map cheat sheet

- Engine: `cma/cma/` (config, hooks, activity, cli, mcp/, recorder/, retriever/, storage/)
- Bundle (ships with `cma add`): `cma/cma/_bundle/{agents,prompts,obsidian,memory_log}/`
- Whitepaper source: `cma/docs/build_whitepaper.py`
- Tests: `cma/tests/`
- Demo agent: `C:\Users\danny\OneDrive\Desktop\email-checker\`

---

## Recent feedback memories captured

In `C:\Users\danny\.claude\projects\C--Users-danny-OneDrive-Desktop-claude-projects\memory\`:

- `feedback_dont_default_to_hooks.md` — bundle for availability, hooks for invocation. Both used; don't conflate.
- `feedback_commit_dont_overquestion.md` — propose plan and start, reserve AskUserQuestion for binary forks
- `feedback_writing_style.md` — no em-dashes, no AI-isms, short sentences
- `project_cma.md` — project context, whitepaper as source of truth
- `feedback_project_organization.md` — Danny's desktop is the OneDrive-synced one

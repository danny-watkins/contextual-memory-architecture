# CMA Session Log

A running log of where we are in the build, so a cold-start return to this project takes minutes instead of hours.

Last updated: 2026-05-14

---

## Where we are right now

CMA is a working drop-in memory layer that auto-fires on every Claude Code task, runs the full Retriever pipeline (hybrid BM25+embeddings, graph traversal, fragment extraction, spec persistence), captures the prompt + session, and exposes everything through a live HTML dashboard. End-to-end loop is functional on the email-checker demo.

**Source of truth:** `docs/CMA_Whitepaper_v0.5.pdf` (built from `docs/build_whitepaper.py`).

**Reference install:** `examples/email-checker/` — a stand-in agent project we use to exercise CMA end-to-end. Run `cma add` inside that directory after `pip install -e ".[all]"` to see the full loop.

**Status:** all 202 tests pass. Architecture matches the whitepaper *except* for the two-tier ingestion model added 2026-05-13 (memory vs substrate) — see the 2026-05-13 entry below; whitepaper §6.2 needs an update before the next public release.

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
3. The email-checker demo lives at `examples/email-checker/` -- run `cma add` inside it after the editable pip install
4. Dashboard will appear at `examples/email-checker/cma/memory_log/dashboard.html` after `cma add` runs

---

## 2026-05-13 — First external dogfood: job-tracker install

Installed CMA into `job-tracker/` (Danny's real job-application automation project, ~221 markdown notes after ingest). The install surfaced three bugs and one architectural mismatch worth fixing before the next external user runs `cma add` on a real project.

### Bugs fixed

**`cma retrieve --json` emitted corrupt JSON** (commit `4e8c215`). Three bugs in one CLI path:
- `rich.Console.print` soft-wrapped the dumped JSON, inserting `\n` inside string fields. Switched to `sys.stdout.buffer.write(out.encode("utf-8"))` so wrapping is impossible.
- The "Context budget" gauge printed to stdout *after* the JSON, breaking any `json.loads` on the captured stream. Now suppressed in `--json` mode.
- Plain `print()` crashed on Windows cp1252 when fragments contained unicode (e.g. `→` arrows from Danny's company notes). UTF-8 bytes route bypasses that too.
- Regression test in `tests/test_cli.py::test_retrieve_json_output_is_valid_json` exercises all three.

### Architectural changes (commit `7b32cf8`)

The dogfood graph view became a hairball — 221 nodes, several mega-hubs with 200+ outbound edges. Root cause: CMA was treating all ingested content as first-class memory citizens. Code, configs, READMEs, JSON shortlists — all got graph nodes and wikilinks.

**Two-tier ingestion (memory vs substrate).** Every ingested note now carries `tier: memory|substrate` frontmatter:
- Memory tier (decisions, patterns, projects, companies, skills, sessions, postmortems, evals): lands in `020-sources/`, gets graph colors by `type:`, contributes to the visible map.
- Substrate tier (code, configs, docs, data, changelogs): lands in a new `020-substrate/` folder, dimmed in the default Obsidian view. Still indexed for BM25 + embeddings — retrieval can still walk substrate, the user just doesn't see it cluttering the graph.

**Fan-out caps on auto-generated nodes.** `context_spec` and project notes were unbounded wikilink emitters. Now:
- Context specs: max 8 source wikilinks + 12 relationship-map wikilinks. Overflow renders as plain titles in body prose.
- Project notes: max 12 wikilinks per detected type. Same overflow rule.
- Constants in `cma/retriever/spec_builder.py` and `cma/ingest.py`.

**Default Obsidian colors switched from retrieve-count heatmap to `type:`-keyed.** The heatmap needed months of retrieval data to differentiate anything; type is available at ingest. New palette is in `cma/_bundle/obsidian/graph.json`. Heatmap stays as a future fallback.

**Dashboard groups by calendar date, not process session id.** `_session_id()` is per-process, so every `cma index` / `cma retrieve` / `cma add` invocation got its own "session" in the dashboard — Danny's first dogfood conversation showed 4 phantom sessions. The JSONL keeps the session_id for forensics; the UI now collapses by `ts[:10]`. New `fmtDayTitle` shows Today / Yesterday / weekday.

### Tests

- `tests/test_spec_builder.py` (new) — wikilink caps regression: sources, relationship map, exclusions all bounded; overflow appears as plain titles.
- `tests/test_cli.py::test_ingest_folder_routes_mixed_tiers_to_separate_folders` (new) — fixture with a decision + a `.py` file; asserts decision → `020-sources/`, code → `020-substrate/`, both with correct `tier:` frontmatter.
- Existing ingest tests refactored to use a tier-agnostic `_ingested_notes` helper since they don't care about the split.
- 191 → 196 passing.

### What the whitepaper needs

§6.2 ("Initial ingestion and the training phase") currently describes a one-tier model — every file becomes a memory node. The text needs:
- A new subsection on memory vs substrate routing
- The `tier:` frontmatter field documented in the schema list (§4 or wherever the YAML schema lives)
- A note that substrate is retrievable but visually filtered by default

The LinkedIn update from 2026-05-12 emphasized the graph view as the headline demo — those screenshots are now misleading (they don't show two-tier coloring). The next LinkedIn post should re-shoot with a fresh `cma add` on a real project to show the new defaults.

### What the dogfood project (job-tracker) needs

The `core/retrieve_context.py` in `job-tracker/` got a 4th hop: CMA Retriever via the Python API (`Retriever.from_project`), called from inside the existing structured-stats retrieval. Bumped `MAX_CONTEXT_CHARS` from 2000 → 2600 to fit the new block. Not in this repo; recorded here so the next CMA installer knows the integration pattern.

---

## Open threads (added 2026-05-13)

9. **Existing vaults don't have `tier:` frontmatter.** ~~Need a `cma migrate-tier` command.~~ Resolved later 2026-05-13 — see the migrate-tier note below.

10. **Whitepaper §6.2 is now stale.** Re-build `docs/CMA_Whitepaper_v0.5.pdf` after the two-tier subsection lands. Probably v0.6.

11. **`cma retrieve` CLI doesn't call `log_activity`.** Noticed while testing the dashboard fix — CLI retrievals are invisible in the memory log because only ingest and one other path call into activity logging. Worth wiring up so the dashboard reflects all retrieval activity, not just hook-fired ones.

12. **Two-tier filter in `.obsidian/graph.json` is colors-only, not search.** Substrate gets dimmed but still shows. A more aggressive default would set `"search": "-[\"tier\":\"substrate\"]"` so substrate is hidden by default and the user clicks to reveal. Held off to be less surprising on first install. Worth A/B-ing against new users.

---

## 2026-05-13 (later) — `cma migrate-tier` lands

Closes thread #9. New command for users with pre-two-tier vaults:

```
cma migrate-tier [--project PATH] [--move-files] [--dry-run]
```

What it does:
- Walks the vault, reads each `.md`, infers `tier:` from existing `type:` via `_classify_tier()` (the same function the ingest pipeline uses).
- Backfills `tier: memory|substrate` frontmatter on notes that don't already have it. Notes that already declared a tier are left alone.
- With `--move-files`, additionally relocates substrate notes from `020-sources/<project>/` to `020-substrate/<project>/` so the folder layout matches the frontmatter convention.
- `--dry-run` previews counts + tier breakdown without writing.
- Skips `011-archive/` so previously-archived notes stay parked.

Implementation: `cma/lifecycle/migrate_tier.py`, exposed via `cma/lifecycle/__init__.py`. CLI added to `cma/cli.py` as `migrate-tier` (kebab-case command, `migrate_tier_cmd` Python name to avoid shadowing the module).

Tests in `tests/test_migrate_tier.py` cover backfill, dry-run safety, `--move-files` relocation, and CLI surface. 202/202 passing.

Dogfood: ran against the real job-tracker vault. Result was 36 memory + 212 substrate out of 248 notes — matches the audit numbers from earlier today (152 docs + 39 code + 21 configs were the substrate suspects, and that's exactly what came out).

### Whitepaper implication

§6.2 (now slated for v0.6) should mention the migration command as the upgrade path for users who installed under v0.5 — otherwise their graph view stays a hairball after the upstream change.

---

## 2026-05-13 (even later) — entity_type recognition + tier in graph nodes

Running migrate-tier on Danny's real job-tracker vault surfaced a misclassification problem: ~144 company/skill notes (from his `obsidian_kb/`) had been ingested as `type: documentation` (the fallback) because `_detect_type` didn't recognize the `companies/`, `skills/` folder convention. They had `entity_type: company` set as the user's semantic tag, but the migration dutifully classified `documentation → substrate` per the literal `type:` field. End result: 144 actual memory-tier notes got demoted to substrate.

Four related fixes (commit forthcoming):

1. **`_detect_type` learns more folders.** `companies/`, `skills/`, `people/`, `postmortems/`, `sessions/` are now recognized at ingest time and routed to the right semantic type. New installs from Obsidian-style KBs (which is most of them) will classify correctly.

2. **migrate-tier honors `entity_type`.** Added `_effective_type(meta)` which prefers `entity_type:` over `type:` when both are present. This is the Obsidian-KB convention — `type` is often a CMA-internal tag (added by ingest), while `entity_type` is the user's semantic claim ("this is a company"). When they disagree, the user's intent wins.

3. **migrate-tier corrects mismatches, not just blanks.** Old behavior: skip notes that already have a `tier:`. New behavior: if the existing tier disagrees with what `_effective_type` implies, rewrite and (with `--move-files`) reverse-relocate. So a substrate note that should be memory gets pulled back to `020-sources/` automatically.

4. **`tier` is now a first-class field on `MemoryRecord`, the graph node, and `nodes.json`.** Previously the tier sat only in raw frontmatter — downstream consumers (graph audits, retrieval policies, Obsidian filters) couldn't see it without re-parsing the markdown. Added to `MemoryRecord` schema (`tier: str = "memory"`), surfaced in `build_graph()` and the `cma/cache/graph/nodes.json` manifest.

Tests:
- `tests/test_migrate_tier.py::test_migrate_honors_entity_type_over_type` — pin entity_type → memory routing.
- `tests/test_migrate_tier.py::test_migrate_corrects_misclassified_substrate_back_to_memory` — verify the reverse-move from `020-substrate/` to `020-sources/` when the tier is corrected.
- 204 total (202 → 204).

Dogfood result on job-tracker: 144 moved back to memory. Final tier breakdown: 315 memory / 68 substrate. Folder layout now matches frontmatter.

### Remaining hairball cause (open)

After all that, the graph still shows mega-hubs. Root cause now is **159 old context_specs from before the fan-out cap landed**, averaging 47.8 outbound edges each (7,604 total). Those were written by the pre-cap `render_spec_as_vault_note` and are now historical artifacts. Three options for resolution; not yet decided:
- Delete them (they're auto-generated, no user-authored content)
- Archive to `011-archive/` (preserves history, removes from default views)
- Add a `cma curator` pass that re-renders existing specs in place with the cap applied

Worth deciding once before the next public demo.

---

## 2026-05-14 — Phase 1 testing pass on job-tracker install (in progress)

Working through `docs/TESTING_SUITE.md` Phase 1 (smoke tests) against the real job-tracker install. Each prompt fired by the user inside Claude Code so the `UserPromptSubmit` hook runs naturally. Findings logged live; fixes to be shipped to `origin/main` per iteration-loop convention.

### Test #1 — "what do you know about Anthropic?"

**Expected:** Top result is `[[anthropic]]` company note (which has structured Strengths / Gaps / Skills section, `retrieve_count: 13`, `avg_fit_score: 0.8`).

**Actual:** Top results were:
1. `generate_cover_letter` (code, node_score 0.511) — cover-letter prompt template, only tangentially relevant
2. Six `*_greenhouse_shortlist` configs — JSON files containing the literal string `"Anthropic"` as a field value
3. Some shortlist `.json` aggregates and a numeric-ID note

The dedicated `companies/anthropic.md` did **not** appear in the top fragments at all. Both `companies/anthropic.md` and `skills/anthropic.md` exist in the vault and are wikilinked from many notes — retrieval still missed them.

### Test #2 — "show me jobs where I scored over 80% fit"

**Expected:** Shortlist notes (filtered to ≥0.8 fit) + `outcomes_summary.md` pattern note.

**Actual:**
- `generate_cover_letter` (code, top again, score 0.502)
- `builtin_scout` (code that contains the literal identifier `fit_score`)
- Skill nodes `r`, `python`, `dbt`, `elt`, `javascript`, `rag` (graph-traversed from `generate_cover_letter`'s wikilinks)
- `stripe_cover_letter`, `blueorigin_cover_letter` (more code)

**Zero** shortlist notes retrieved. **Zero** `outcomes_summary.md` — even though it exists at `vault/020-sources/patterns/outcomes_summary.md`.

### Root cause hypothesis (Bug C — retrieval rank quality)

Two reinforcing failure modes:

1. **BM25 fragment scoring rewards rare-keyword density in code/config.** Terms like `Anthropic`, `fit_score`, `cover_letter` appear as string literals or identifiers in `.py` files and JSON aggregates. Per-chunk frequency in those files dwarfs the same terms appearing in a paragraph of a structured prose note (which is "diluted" by other content). So code wins seed selection.
2. **Graph traversal anchors on the bad seed.** Once `generate_cover_letter` is seed #1, BFS expands its wikilinks → which are *skill* nodes. The traversal never reaches `shortlist` or `outcomes_summary` because the bad seed has no edge to them.

This is the concrete manifestation of Open Thread #1 ("Fragment-level scoring is BM25-only") — but worse than the thread originally framed. It's not just *which paragraph* gets picked from a good source; it's *which source* gets picked at all. Code beats prose at the source level.

### Proposed fixes (Bug C)

In rough order of cost/benefit:

1. **Down-weight code/config nodes at seed selection.** Multiply node_score by a type prior — `code: 0.6`, `config: 0.7`, `note/memory: 1.0`. Cheap to implement, addresses the immediate symptom. Risk: hurts genuine code-search queries; mitigate by detecting code-intent queries (contains identifier-looking tokens, file extensions, etc.).
2. **Boost `tier: memory` over `tier: substrate` in seed scoring.** We already have the tier field on graph nodes (added 2026-05-13). Multiply scores: memory ×1.0, substrate ×0.5. The user's curated memory notes should outrank auto-ingested source files for semantic queries by default.
3. **Hybrid fragment scoring (the actual fix in Open Thread #1).** Add an embedding pass on fragments, not just on nodes. BM25 stays for keyword anchoring; cosine sim on a sentence embedding handles the prose case where the answer is paraphrased, not literal. Adds ~50-150ms per retrieve; worth it.
4. **Backlink reinforcement.** Notes with high inbound wikilink count from `tier: memory` neighbors get a small seed bonus. `[[anthropic]]` is heavily backlinked from shortlists, sessions, etc. — that signal is currently unused at seed time.

Plan: ship #1 + #2 immediately as a one-commit guardrail (small, testable). Hold #3 for its own commit with a benchmark harness over Phase 1 prompts (we now have ground-truth-expected-source pairs from the testing suite — useful as eval set). #4 after #3 lands.

### Bug A — Dashboard "Today" groups by UTC, not local date

Dashboard shows "Today · 2026-05-14 · 28 events · 01:13–20:08 UTC". For a PT user, 01:13 UTC on 2026-05-14 is 18:13 PT on 2026-05-13. So yesterday-evening-PT events are folded into today's row.

**Fix:** Dashboard renderer groups events by `datetime.fromisoformat(ts).astimezone().date()` (local) rather than UTC date. One-line change in the renderer; render section labels with the local TZ abbreviation so it's clear what timezone we're showing.

### Bug B — Collapsed Today-row chips drop `prompt`/`retrieve` events

Today's row shows "28 events" but only chips `index: 8 · ingest: 1` in the collapsed preview. The other 19 are `prompt`/`retrieve`/`stop` events that the collapsed-preview chip renderer omits. From the user's POV "nothing happened" after a retrieve — but the event is in `activity.jsonl`; the row just hides it until expanded.

**Fix:** Include all non-zero event types in the collapsed-preview chips, with `prompt` and `retrieve` prioritized (they're the most diagnostic — the user cares whether their queries fired). One-line filter change in the renderer.

### Test #3 — "what skills am I weakest in?"

**Expected:** `skills/*` notes with low `candidate_level` + `outcomes_summary.md`.

**Actual:**
1. `blueorigin_cover_letter` (code, top, 0.471)
2. `generate_cover_letter` (code)
3. Skill nodes `javascript`, `bash`, `mysql` — graph-traversed from cover-letter seeds, not selected on `candidate_level`
4. `update_kb` (code)
5. `anthropic` (first memory node this run — reached via shortlist backlinks, not relevant to the query topic)
6. `2026-04-21_1205_greenhouse_shortlist`, `braintrust_cover_letter`, `stripe_cover_letter`

**Zero** `outcomes_summary`. Skill notes appeared only as graph hops, not chosen for their `candidate_level` content.

**Bug C confirmed three-for-three.** Across all three Phase 1 prompts, the top seed was code (cover-letter or scout). Graph traversal works fine; the upstream seed selection is what's broken. Mildly encouraging signal in Test #3: BFS did reach a memory note (`[[anthropic]]`) when seeded poorly — so the traversal half of the pipeline is healthy, validating that fixes #1 + #2 (down-weight code + boost memory-tier at seed selection) are the right surgical target.

### Bug D — Dashboard sort order: newest events should be on top

User feedback during Phase 1: the activity feed shows oldest-first within each day group, so to see what just fired you have to scroll. Should be newest-first (descending by `ts`) so the latest prompt/retrieve sits at the top of its group.

**Fix:** Reverse the per-group event sort in the dashboard renderer (`sort(key=ts, reverse=True)`). One-line change.

### Next

- Phase 1 complete. Three concrete bugs (A, B, D dashboard; C retriever) with proposed fixes.
- Ship Bugs A + B + D as a single dashboard commit (all in the renderer; ~5-10 LoC total).
- Ship Bug C fixes #1 + #2 (code/config down-weight + memory-tier seed boost) as a single retriever commit with a regression test that seeds the three Phase 1 prompts and asserts the expected canonical sources appear in top-K.
- Re-run Phase 1 to confirm fixes hold before moving to Phase 2.

---

## File map cheat sheet

- Engine: `cma/` (config, hooks, activity, cli, mcp/, recorder/, retriever/, storage/)
- Bundle (ships with `cma add`): `cma/_bundle/{agents,prompts,obsidian,memory_log}/`
- Whitepaper source: `docs/build_whitepaper.py`
- Tests: `tests/`
- Demo agent: `examples/email-checker/`

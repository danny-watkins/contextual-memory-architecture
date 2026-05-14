# CMA Testing Suite — Live Install Walkthrough

A prompt-driven test plan for exercising a real CMA install end-to-end: the auto-fire Retriever (UserPromptSubmit hook), the Recorder (Stop hook), the MCP tools, and the visual surfaces (dashboard + Obsidian graph). Designed to run inside an agent project that has CMA installed via `cma add`.

Use this when:
- You want to verify a fresh `cma add` is functional
- You want to surface bugs / regressions before a public demo
- You're testing a recent change to the engine

Update findings into `SESSION_LOG.md` under a new dated entry. Every fix uncovered ships to the CMA repo immediately per the iteration-loop convention.

---

## Setup

1. Open a new Claude Code session in the project directory (the one that has `.claude/`, `.mcp.json`, and `CLAUDE.md` from `cma add`). Hooks only fire inside Claude Code, not from bare CLI.
2. Open the dashboard in a browser tab: `file:///<project>/cma/memory_log/dashboard.html`. It auto-refreshes every 5 seconds.
3. If you want the visual flash on retrieval, open Obsidian with `cma/vault/` as the vault, switch to graph view (Ctrl+G).

---

## Phase 1 — Smoke tests (does it fire?)

| # | Prompt | What to watch | Bug if |
|---|---|---|---|
| 1 | `what do you know about Anthropic?` | A `# Context Spec` block prepends the turn. Should cite `[[anthropic]]` with strengths/gaps + related skill nodes. Dashboard logs the event within ~5s. | No Context Spec block / no dashboard event / silent hook failure. |
| 2 | `show me jobs where I scored over 80% fit` | Should pull shortlist notes + outcomes_summary. | Returns nothing, or only matches the literal word "shortlist." |
| 3 | `what skills am I weakest in?` | Pulls skills/* notes with low `candidate_level` and hits `outcomes_summary.md`. | Misses the cross-skill aggregate in patterns. |

---

## Phase 2 — Retrieval quality

| # | Prompt | What to watch | Bug if |
|---|---|---|---|
| 4 | `I'm applying to Greenlight for a data role — tailor my resume` | Retrieves `[[greenlight]]` + related skills + past outcome. | Generic resume advice with no company-specific context. |
| 5 | `what's our response rate across all applications?` | Single number cited from `outcomes_summary.md`. | LLM hallucinates a number instead of citing the patterns file. |
| 6 | `find me companies similar to Hiya based on tech stack` | Semantic retrieval walks the skills graph to find peers. | Returns only exact name matches. |

---

## Phase 3 — MCP tools (explicit calls)

These bypass the auto-load and exercise the MCP server directly.

| # | Action | What to watch |
|---|---|---|
| 7 | Ask the agent to call `mcp__cma__search_notes("contract roles")` | Lists matching notes ordered by score. |
| 8 | Ask it to call `mcp__cma__get_backlinks("anthropic")` | Returns shortlists + patterns that wikilink to Anthropic. |
| 9 | Ask `mcp__cma__retrieve` with `max_depth=3, beam_width=8` for a deep walk | More fragments, longer spec note in `vault/008-context-specs/`. Verify wikilinks under `## Sources` are capped at 8. |

---

## Phase 4 — Recorder (write path)

| # | Action | What to watch | Bug if |
|---|---|---|---|
| 10 | After a substantive exchange, end the session (`/exit`) | New session note in `vault/002-sessions/<timestamp>.md` with summary, task_id, links to retrieved sources. | Stop hook didn't fire / session note missing / empty body. |
| 11 | In a fresh session: `decided we'll deprioritize remote-only roles. record this as a decision.` Watch for an `mcp__cma__record_completion` call. | Creates a note in `003-decisions/` with `type: decision, status: proposed`. Confidence-gated. | Writes accepted without confidence check / wrong folder. |

---

## Phase 5 — Visual surface

- **Dashboard**: a single "Today" group should populate as you prompt. If you see multiple "Sessions" instead of one Today row, day-grouping didn't take.
- **Obsidian graph**: substrate (gray) should be visually distinct from memory (colored by type). Each retrieve flashes source nodes green for ~5s.
- **Context spec notes**: open one in `vault/008-context-specs/`. Verify `## Sources` has at most 8 `[[wikilinks]]` followed by plain titles (this is the fan-out cap).

---

## Phase 6 — Stress / regression probes

| # | Probe | Why it matters |
|---|---|---|
| 12 | Edit a vault file in another tab, then ask about its contents here. | Tests whether retrieval reflects edits. It WON'T until `cma index` runs. Confirms the cache-staleness behavior — decide if auto-reindex on file change is worth adding. |
| 13 | Ask 5 prompts in quick succession. | Watch dashboard — should land under one "Today" row. Each produces a context_spec note; the graph shouldn't rehairball. |
| 14 | Ask something with no good match (e.g. about a company you haven't applied to). | Should return gracefully — thin Context Spec + plain LLM answer. Bug: hard fail or hallucinated history. |

---

## Open threads to watch for during testing

From `SESSION_LOG.md` "Open threads":

1. **Fragment-level scoring is BM25-only.** Note any prompt where a "good" source returns a weirdly-chosen paragraph.
2. **Dashboard source ordering** by `tokens_extracted` — high-volume but less-relevant sources can outrank relevant short ones.
3. **Per-hook embedding model load** is ~2-3s cold-start. Concerning if first-prompt latency is much higher.
4. **MCP server events** appear in their own session block separate from Claude Code — cosmetic; might not show in the day-grouped UI consistently.
5. **Source attribution boilerplate** ("From [[project]] / `path/file`") cluttering fragments.
6. **Debug breadcrumbs** in `cma/memory_log/hook_debug.log` still being written — should be flag-gated before release.

---

## After the run

- Add a 2026-MM-DD entry to `SESSION_LOG.md` summarizing what worked, what broke, what got fixed.
- Each bug fix shipped to the CMA repo gets its own commit + push to `origin/main`.
- Update or add open threads as needed.

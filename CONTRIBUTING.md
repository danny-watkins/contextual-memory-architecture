# Contributing

Thanks for being curious enough to read this file.

CMA is in **v0.5 alpha**. The architecture is settled and documented in the whitepaper; the implementation works end-to-end on the demo project; but the system has not yet been pushed against many agent shapes, large vaults, or diverse workflows. That's where contributors come in.

## Before you start

1. **Read the whitepaper** (`docs/CMA_Whitepaper_v0.5.pdf`). It's the source of truth for the architecture. The code matches it; the README condenses it.
2. **Skim `SESSION_LOG.md`** at the repo root. It's a candid snapshot of where the build stands, what works, and what's still rough. The "Open threads" section is roughly ranked by payoff — those are the best places to start.
3. **Run the tests**:
   ```bash
   pip install -e ".[all]"
   python -m pytest
   ```
   You should see ~190 tests pass. If you can't get a green run, please open an issue with your platform/Python version — that's a useful bug to know about.

## How to propose work

- **Small things** — typos, docs, additional test coverage, obvious bug fixes — feel free to open a PR directly.
- **Anything bigger** — new features, design changes, refactors — please open an issue first so we can shape direction together before you invest time. The early-stage trap is good code in the wrong direction.

## Style and scope

- Match the existing code style. Type hints, short docstrings explaining WHY non-obvious choices were made (not what the code does — names already do that), no defensive error handling for impossible cases.
- Don't add features beyond what the linked issue requires. If you notice adjacent cleanup, file a separate issue.
- Tests are required for new behavior. Tests are not required for refactors that don't change behavior, but adding them rarely hurts.
- The vault format is part of the public contract. Don't change frontmatter schema or wikilink semantics without opening a discussion first.

## Where the seams are

- **Engine code**: `cma/cma/` — config, hooks, activity, retriever, recorder, mcp, storage
- **Bundled files that ship with `cma add`**: `cma/cma/_bundle/` — sub-agents, prompts, Obsidian config, dashboard template
- **Tests**: `cma/tests/`
- **Whitepaper source**: `cma/docs/build_whitepaper.py`
- **Slideshow source**: `cma/docs/build_slideshow.py`
- **Demo agent**: `cma/examples/email-checker/`

## Reporting bugs

Open an issue with:
- What you ran
- What you expected
- What happened
- Platform + Python version
- Any relevant chunk of `cma/memory_log/activity.jsonl` or `hook_debug.log` (set `CMA_HOOK_DEBUG=1` to enable hook debug breadcrumbs)

## License

By contributing you agree your contributions are licensed under the same [MIT](LICENSE) license as the project.

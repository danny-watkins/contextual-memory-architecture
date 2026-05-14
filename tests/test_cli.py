from pathlib import Path

from typer.testing import CliRunner

from cma.cli import app

runner = CliRunner()


def _ingested_notes(project: Path, project_name: str) -> list[Path]:
    """Return ingested notes from either tier folder.

    With the two-tier ingest, memory-tier content lands in `020-sources/` and
    substrate (code/configs/docs) lands in `020-substrate/`. Tests that only
    care that ingestion happened (not which tier) should use this helper.
    """
    notes: list[Path] = []
    for tier in ("020-sources", "020-substrate"):
        tier_dir = project / "cma" / "vault" / tier / project_name
        if tier_dir.exists():
            notes.extend(tier_dir.glob("*.md"))
    return notes


def test_init_creates_project_structure(tmp_path: Path):
    project = tmp_path / "agent-1"
    result = runner.invoke(app, ["init", str(project)])
    assert result.exit_code == 0, result.output
    assert (project / "cma" / "config.yaml").exists()
    assert (project / "cma" / "vault" / "000-inbox").is_dir()
    assert (project / "cma" / "vault" / "003-decisions").is_dir()
    assert (project / "cma" / "memory_log" / "write_logs").is_dir()
    assert (project / "cma" / "memory_log" / "proposals").is_dir()
    assert (project / "cma" / "memory_log" / "dashboard.html").exists()
    assert (project / "cma" / "cache" / "graph").is_dir()
    assert (project / "cma" / "vault" / "000-inbox" / "Welcome.md").exists()


def test_init_refuses_existing_without_force(tmp_path: Path):
    project = tmp_path / "agent-1"
    runner.invoke(app, ["init", str(project)])
    result = runner.invoke(app, ["init", str(project)])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_init_force_overwrites(tmp_path: Path):
    project = tmp_path / "agent-1"
    runner.invoke(app, ["init", str(project)])
    result = runner.invoke(app, ["init", str(project), "--force"])
    assert result.exit_code == 0


def test_index_then_graph_health(tmp_path: Path):
    project = tmp_path / "agent-1"
    runner.invoke(app, ["init", str(project)])

    # Add a linked note so the graph has more than the seed notes
    (project / "cma" / "vault" / "003-decisions" / "Async Queue.md").write_text(
        """---
type: decision
status: accepted
confidence: 0.9
---
# Async Queue
Links to [[Welcome]].
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["index", str(project)])
    assert result.exit_code == 0, result.output
    assert "Parsed 3 notes" in result.output
    assert (project / "cma" / "cache" / "graph" / "nodes.json").exists()

    health = runner.invoke(app, ["graph", "health", str(project)])
    assert health.exit_code == 0, health.output
    assert "Total notes" in health.output


def test_index_fails_when_vault_missing(tmp_path: Path):
    result = runner.invoke(app, ["index", str(tmp_path)])
    assert result.exit_code == 1
    assert "Vault not found" in result.output


def test_index_no_embeddings_writes_bm25_only(tmp_path: Path):
    project = tmp_path / "agent"
    runner.invoke(app, ["init", str(project)])
    result = runner.invoke(app, ["index", str(project), "--no-embeddings"])
    assert result.exit_code == 0, result.output
    assert (project / "cma" / "cache" / "bm25" / "index.pkl").exists()
    assert (project / "cma" / "cache" / "graph" / "nodes.json").exists()
    # Embeddings should not be written
    assert not (project / "cma" / "cache" / "embeddings" / "embeddings.npy").exists()


def test_ingest_folder_detects_documentation_and_inlines_markdown(tmp_path: Path):
    project = tmp_path / "agent"
    source = tmp_path / "source"
    (source / "app").mkdir(parents=True)
    (source / "app" / "README.md").write_text(
        "# Demo App\n\nUses [[Existing Concept]] for orchestration.", encoding="utf-8"
    )
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        [
            "ingest-folder",
            str(source),
            "--project",
            str(project),
            "--extensions",
            "md",
            "--index",
        ],
    )

    assert result.exit_code == 0, result.output
    # Documentation is substrate tier (it describes the code, it isn't memory),
    # so it lands under 020-substrate/ — searchable but visually filtered out
    # of the default graph view.
    source_notes = list((project / "cma" / "vault" / "020-substrate" / "app").glob("*.md"))
    assert len(source_notes) == 1
    text = source_notes[0].read_text(encoding="utf-8")
    assert "type: documentation" in text
    assert "tier: substrate" in text
    assert "source_project: app" in text
    assert "From [[app]]" in text
    assert "[[Existing Concept]]" in text
    assert "```md" not in text
    assert "```markdown" not in text
    project_note = project / "cma" / "vault" / "001-projects" / "app.md"
    assert project_note.exists()
    project_text = project_note.read_text(encoding="utf-8")
    assert "type: project" in project_text
    assert "tier: memory" in project_text
    assert "### Documentation" in project_text
    assert (project / "cma" / "cache" / "graph" / "nodes.json").exists()


def test_ingest_folder_detects_code_and_uses_fenced_block(tmp_path: Path):
    project = tmp_path / "agent"
    source = tmp_path / "source"
    (source / "app").mkdir(parents=True)
    (source / "app" / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        ["ingest-folder", str(source), "--project", str(project), "--extensions", "py"],
    )

    assert result.exit_code == 0, result.output
    # Code is substrate tier — routes to 020-substrate/.
    source_notes = list((project / "cma" / "vault" / "020-substrate" / "app").glob("*.md"))
    assert len(source_notes) == 1
    text = source_notes[0].read_text(encoding="utf-8")
    assert "type: code" in text
    assert "tier: substrate" in text
    assert "```python" in text
    assert "def hello()" in text
    # And it must NOT also be in 020-sources/.
    assert not list((project / "cma" / "vault" / "020-sources").glob("**/*.md"))


def test_ingest_folder_detects_decision_in_decisions_dir(tmp_path: Path):
    project = tmp_path / "agent"
    source = tmp_path / "source"
    (source / "app" / "decisions").mkdir(parents=True)
    (source / "app" / "decisions" / "use-postgres.md").write_text(
        "# Use Postgres\n\nWe picked Postgres because we need transactions.\n",
        encoding="utf-8",
    )
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        ["ingest-folder", str(source), "--project", str(project), "--extensions", "md"],
    )

    assert result.exit_code == 0, result.output
    # Decisions are memory tier — stay under 020-sources/.
    source_notes = list((project / "cma" / "vault" / "020-sources" / "app").glob("*.md"))
    assert len(source_notes) == 1
    text = source_notes[0].read_text(encoding="utf-8")
    assert "type: decision" in text
    assert "tier: memory" in text


def test_ingest_folder_routes_mixed_tiers_to_separate_folders(tmp_path: Path):
    """Drop a memory-tier note (decision) and a substrate note (code) into the
    same source tree; assert they end up in different vault folders so the
    default graph view can filter substrate out."""
    project = tmp_path / "agent"
    source = tmp_path / "source"
    (source / "app" / "decisions").mkdir(parents=True)
    (source / "app" / "decisions" / "pick-postgres.md").write_text(
        "# Pick Postgres\n\nNeed transactions; ACID matters here.\n",
        encoding="utf-8",
    )
    (source / "app" / "main.py").write_text(
        "def hello():\n    return 'world'\n", encoding="utf-8"
    )
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        ["ingest-folder", str(source), "--project", str(project), "--extensions", "md,py"],
    )
    assert result.exit_code == 0, result.output

    memory_notes = list((project / "cma" / "vault" / "020-sources").glob("**/*.md"))
    substrate_notes = list((project / "cma" / "vault" / "020-substrate").glob("**/*.md"))
    memory_titles = {p.stem for p in memory_notes}
    substrate_titles = {p.stem for p in substrate_notes}
    assert any("postgres" in t for t in memory_titles), memory_titles
    assert any("main" in t for t in substrate_titles), substrate_titles
    # Each note must declare its tier explicitly so downstream tools (graph
    # filters, retrieval policies) can rely on it.
    for n in memory_notes:
        assert "tier: memory" in n.read_text(encoding="utf-8")
    for n in substrate_notes:
        assert "tier: substrate" in n.read_text(encoding="utf-8")


def test_ingest_folder_skips_files_under_min_chars(tmp_path: Path):
    project = tmp_path / "agent"
    source = tmp_path / "source"
    (source / "app").mkdir(parents=True)
    (source / "app" / "__init__.py").write_text("", encoding="utf-8")
    (source / "app" / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        ["ingest-folder", str(source), "--project", str(project), "--extensions", "py"],
    )

    assert result.exit_code == 0, result.output
    notes = _ingested_notes(project, "app")
    assert len(notes) == 1
    assert "main" in notes[0].name


def test_ingest_folder_exclude_glob_skips_matching_paths(tmp_path: Path):
    project = tmp_path / "agent"
    source = tmp_path / "source"
    (source / "app" / "tests").mkdir(parents=True)
    (source / "app" / "main.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    (source / "app" / "tests" / "test_main.py").write_text(
        "def test_hello():\n    assert True\n", encoding="utf-8"
    )
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        [
            "ingest-folder",
            str(source),
            "--project",
            str(project),
            "--extensions",
            "py",
            "--exclude-glob",
            "*/tests/*",
        ],
    )

    assert result.exit_code == 0, result.output
    notes = _ingested_notes(project, "app")
    assert len(notes) == 1
    assert notes[0].stem == "main"


def test_ingest_folder_dry_run_writes_nothing(tmp_path: Path):
    project = tmp_path / "agent"
    source = tmp_path / "source"
    source.mkdir()
    (source / "note.md").write_text("# Note\n\nA real note with content.", encoding="utf-8")
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        ["ingest-folder", str(source), "--project", str(project), "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "DRY RUN" in result.output
    assert not (project / "cma" / "vault" / "020-sources" / "source").exists()
    assert not (project / "cma" / "vault" / "020-substrate" / "source").exists()


def test_ingest_folder_skips_target_project_when_source_contains_it(tmp_path: Path):
    root = tmp_path / "workspace"
    project = root / "agent"
    external = root / "external"
    external.mkdir(parents=True)
    external.joinpath("note.md").write_text(
        "# External\n\nA real external note.", encoding="utf-8"
    )
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        ["ingest-folder", str(root), "--project", str(project), "--extensions", "md"],
    )

    assert result.exit_code == 0, result.output
    # The external README is documentation -> substrate tier.
    assert _ingested_notes(project, "external"), "external note was not ingested"
    assert not (project / "cma" / "vault" / "020-sources" / "agent").exists()
    assert not (project / "cma" / "vault" / "020-substrate" / "agent").exists()


def test_ingest_folder_filenames_have_single_md_extension(tmp_path: Path):
    project = tmp_path / "agent"
    source = tmp_path / "source"
    (source / "app" / "deep" / "nested").mkdir(parents=True)
    (source / "app" / "README.md").write_text(
        "# App\n\nA real markdown file.", encoding="utf-8"
    )
    (source / "app" / "deep" / "nested" / "thing.py").write_text(
        "def thing():\n    return 42\n", encoding="utf-8"
    )
    runner.invoke(app, ["init", str(project)])

    runner.invoke(app, ["ingest-folder", str(source), "--project", str(project)])

    notes = _ingested_notes(project, "app")
    for n in notes:
        assert not n.name.endswith(".md.md"), f"double extension on {n.name}"
        assert not n.name.endswith(".py.md") or ".py" in n.stem
    names = {n.name for n in notes}
    assert any(n.startswith("README") for n in names)
    assert any("thing" in n for n in names)


def test_ingest_folder_excludes_dot_claude_dir(tmp_path: Path):
    project = tmp_path / "agent"
    source = tmp_path / "source"
    (source / "app" / ".claude").mkdir(parents=True)
    (source / "app" / ".claude" / "settings.json").write_text(
        '{"foo": "bar with enough chars"}', encoding="utf-8"
    )
    (source / "app" / "README.md").write_text(
        "# App\n\nReal documentation here.", encoding="utf-8"
    )
    runner.invoke(app, ["init", str(project)])

    result = runner.invoke(
        app,
        ["ingest-folder", str(source), "--project", str(project)],
    )

    assert result.exit_code == 0, result.output
    notes = _ingested_notes(project, "app")
    assert len(notes) == 1
    assert "README" in notes[0].name


def test_retrieve_returns_relevant_fragment(tmp_path: Path):
    project = tmp_path / "agent"
    runner.invoke(app, ["init", str(project)])
    (project / "cma" / "vault" / "003-decisions" / "Async Capital Call Processing.md").write_text(
        """---
type: decision
title: Async Capital Call Processing
status: accepted
confidence: 0.86
human_verified: true
---

We decided to move capital call processing into an async queue for performance.
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["retrieve", "capital call processing", "--project", str(project), "--json"],
    )
    assert result.exit_code == 0, result.output
    assert "Async Capital Call Processing" in result.output


def test_retrieve_json_output_is_valid_json(tmp_path: Path, monkeypatch):
    """Regression: --json output must be machine-parseable. Three regressions
    this test guards against:
      1. rich.Console.print soft-wraps long strings, inserting newlines INTO
         JSON string fields.
      2. The diagnostic 'Context budget' gauge being written to stdout after
         the JSON, making the stream un-parseable.
      3. Unicode characters in fragment text (e.g. →) crashing print() on
         Windows cp1252.
    The CLI must emit UTF-8 bytes straight to stdout, with all diagnostics
    suppressed or routed elsewhere."""
    import json

    project = tmp_path / "agent"
    runner.invoke(app, ["init", str(project)])
    # Long single-paragraph body (forces wrap at narrow widths) + unicode arrow
    # (forces cp1252 issues on Windows).
    long_body = (
        "This is a deliberately long, single-line decision rationale used to "
        "force terminal soft-wrapping. Arrow: → context hit rate 38% to 78%. " * 6
    )
    (project / "cma" / "vault" / "003-decisions" / "Long Wrap Test.md").write_text(
        f"""---
type: decision
title: Long Wrap Test
status: accepted
---

{long_body}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("COLUMNS", "80")
    result = runner.invoke(
        app,
        ["retrieve", "long wrap test", "--project", str(project), "--json"],
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.stdout)
    assert "fragments" in parsed
    assert parsed["query"] == "long wrap test"


def test_setup_writes_config_changes(tmp_path: Path):
    import yaml

    project = tmp_path / "agent"
    runner.invoke(app, ["init", str(project)])
    # Stdin: integration=2 (Python SDK), embedding=3 (none)
    result = runner.invoke(app, ["setup", str(project)], input="2\n3\n")
    assert result.exit_code == 0, result.output
    with open(project / "cma" / "config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["embedding_provider"] == "none"
    assert "Python SDK integration" in result.output

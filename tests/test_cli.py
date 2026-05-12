from pathlib import Path

from typer.testing import CliRunner

from cma.cli import app

runner = CliRunner()


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
    source_notes = list((project / "cma" / "vault" / "020-sources" / "app").glob("*.md"))
    assert len(source_notes) == 1
    text = source_notes[0].read_text(encoding="utf-8")
    assert "type: documentation" in text
    assert "source_project: app" in text
    assert "From [[app]]" in text
    assert "[[Existing Concept]]" in text
    # Markdown body must NOT be wrapped in a code fence (so wikilinks resolve).
    assert "```md" not in text
    assert "```markdown" not in text
    project_note = project / "cma" / "vault" / "001-projects" / "app.md"
    assert project_note.exists()
    project_text = project_note.read_text(encoding="utf-8")
    assert "type: project" in project_text
    # Project note groups sources by detected type.
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
    source_notes = list((project / "cma" / "vault" / "020-sources" / "app").glob("*.md"))
    assert len(source_notes) == 1
    text = source_notes[0].read_text(encoding="utf-8")
    assert "type: code" in text
    assert "```python" in text
    assert "def hello()" in text


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
    source_notes = list((project / "cma" / "vault" / "020-sources" / "app").glob("*.md"))
    assert len(source_notes) == 1
    assert "type: decision" in source_notes[0].read_text(encoding="utf-8")


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
    source_notes = list((project / "cma" / "vault" / "020-sources" / "app").glob("*.md"))
    assert len(source_notes) == 1
    assert "main" in source_notes[0].name


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
    notes = list((project / "cma" / "vault" / "020-sources" / "app").glob("*.md"))
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
    assert list((project / "cma" / "vault" / "020-sources" / "external").glob("*.md"))
    assert not (project / "cma" / "vault" / "020-sources" / "agent").exists()


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

    notes = list((project / "cma" / "vault" / "020-sources" / "app").glob("*.md"))
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
    notes = list((project / "cma" / "vault" / "020-sources" / "app").glob("*.md"))
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

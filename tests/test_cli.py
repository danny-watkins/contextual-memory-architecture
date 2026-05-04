from pathlib import Path

from typer.testing import CliRunner

from cma.cli import app

runner = CliRunner()


def test_init_creates_project_structure(tmp_path: Path):
    project = tmp_path / "agent-1"
    result = runner.invoke(app, ["init", str(project)])
    assert result.exit_code == 0, result.output
    assert (project / "cma.config.yaml").exists()
    assert (project / "vault" / "000-inbox").is_dir()
    assert (project / "vault" / "003-decisions").is_dir()
    assert (project / "reasoner" / "task_frames").is_dir()
    assert (project / "retriever" / "specs").is_dir()
    assert (project / "recorder" / "completion_packages").is_dir()
    assert (project / ".cma" / "graph").is_dir()
    assert (project / "vault" / "000-inbox" / "Welcome.md").exists()


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
    (project / "vault" / "003-decisions" / "Async Queue.md").write_text(
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
    assert (project / ".cma" / "graph" / "nodes.json").exists()

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
    assert (project / ".cma" / "bm25" / "index.pkl").exists()
    assert (project / ".cma" / "graph" / "nodes.json").exists()
    # Embeddings should not be written
    assert not (project / ".cma" / "embeddings" / "embeddings.npy").exists()


def test_retrieve_returns_relevant_fragment(tmp_path: Path):
    project = tmp_path / "agent"
    runner.invoke(app, ["init", str(project)])
    (project / "vault" / "003-decisions" / "Async Capital Call Processing.md").write_text(
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
    with open(project / "cma.config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["embedding_provider"] == "none"
    assert "Python SDK integration" in result.output

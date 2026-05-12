"""Tests for the MCP server. Skipped if mcp SDK isn't installed."""

from pathlib import Path

import pytest

mcp_module = pytest.importorskip("mcp")

from cma.mcp import server as mcp_server  # noqa: E402


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal project with a tiny vault, ready for the server to load."""
    proj = tmp_path / "agent"
    (proj).mkdir()
    (proj / "cma").mkdir(parents=True, exist_ok=True)
    (proj / "cma" / "config.yaml").write_text(
        "vault_path: ./cma/vault\nindex_path: ./cma/cache\nembedding_provider: none\n",
        encoding="utf-8",
    )
    (proj / "cma" / "vault" / "003-decisions").mkdir(parents=True)
    (proj / "cma" / "vault" / "004-patterns").mkdir(parents=True)
    (proj / "cma" / "vault" / "003-decisions" / "Async Capital Call Processing.md").write_text(
        """---
type: decision
title: Async Capital Call Processing
status: accepted
confidence: 0.86
tags: [capital-calls, performance]
---

We decided to move capital call processing into an async queue.

Uses [[Queue Retry Pattern]].
""",
        encoding="utf-8",
    )
    (proj / "cma" / "vault" / "004-patterns" / "Queue Retry Pattern.md").write_text(
        """---
type: pattern
title: Queue Retry Pattern
status: active
confidence: 0.78
tags: [reliability]
---

External APIs may fail intermittently. Use bounded exponential backoff.

Used by [[Async Capital Call Processing]].
""",
        encoding="utf-8",
    )
    (proj / "cma" / "memory_log").mkdir(parents=True, exist_ok=True)
    (proj / "cma" / "memory_log" / "proposals").mkdir(exist_ok=True)
    (proj / "cma" / "memory_log" / "write_logs").mkdir(exist_ok=True)
    return proj


def _reset_server_state(project: Path) -> None:
    """Manually run the server's init logic without entering stdio loop."""
    mcp_server._PROJECT_PATH = project.resolve()
    mcp_server._RETRIEVER = None
    mcp_server._RECORDER = None
    mcp_server._ensure_loaded()


def test_all_expected_tools_registered():
    """The 10-tool surface from the design spec."""
    expected = {
        "search_notes",
        "get_note",
        "get_outgoing_links",
        "get_backlinks",
        "traverse_graph",
        "search_by_frontmatter",
        "retrieve",
        "record_completion",
        "graph_health",
        "reindex",
    }
    # FastMCP holds tools in a tool manager; pull names off it.
    registered = set(mcp_server.mcp._tool_manager._tools.keys())
    assert expected <= registered, f"missing tools: {expected - registered}"


def test_search_notes_finds_relevant_seed(project: Path):
    _reset_server_state(project)
    results = mcp_server.search_notes("capital call processing")
    assert results
    titles = {r["title"] for r in results}
    assert "Async Capital Call Processing" in titles


def test_get_note_returns_full_content(project: Path):
    _reset_server_state(project)
    note = mcp_server.get_note("Async Capital Call Processing")
    assert note is not None
    assert note["type"] == "decision"
    assert note["status"] == "accepted"
    assert "Queue Retry Pattern" in note["links"]


def test_get_note_returns_none_for_missing(project: Path):
    _reset_server_state(project)
    assert mcp_server.get_note("Does Not Exist") is None


def test_get_outgoing_and_backlinks(project: Path):
    _reset_server_state(project)
    out = mcp_server.get_outgoing_links("Async Capital Call Processing")
    assert "Queue Retry Pattern" in out
    back = mcp_server.get_backlinks("Queue Retry Pattern")
    assert "Async Capital Call Processing" in back


def test_traverse_graph_returns_with_depth(project: Path):
    _reset_server_state(project)
    results = mcp_server.traverse_graph("Async Capital Call Processing", depth=2)
    titles = {r["title"]: r["depth"] for r in results}
    assert "Async Capital Call Processing" in titles
    assert titles["Async Capital Call Processing"] == 0
    assert "Queue Retry Pattern" in titles


def test_search_by_frontmatter_string(project: Path):
    _reset_server_state(project)
    results = mcp_server.search_by_frontmatter("status", "accepted")
    titles = {r["title"] for r in results}
    assert "Async Capital Call Processing" in titles
    assert "Queue Retry Pattern" not in titles  # status=active


def test_search_by_frontmatter_list(project: Path):
    _reset_server_state(project)
    results = mcp_server.search_by_frontmatter("tags", "performance")
    titles = {r["title"] for r in results}
    assert "Async Capital Call Processing" in titles


def test_retrieve_returns_markdown_spec(project: Path):
    _reset_server_state(project)
    md = mcp_server.retrieve("capital call processing", max_depth=2)
    assert "# Context Spec" in md
    assert "Async Capital Call Processing" in md


def test_record_completion_dry_run(project: Path):
    _reset_server_state(project)
    yaml_str = """
task_id: TEST-001
goal: test
summary: test summary
decisions:
  - title: Test Decision
    status: accepted
    confidence: 0.9
"""
    result = mcp_server.record_completion(yaml_str, dry_run=True)
    assert "written" in result
    # Dry run: no files actually created
    assert not (project / "cma" / "vault" / "003-decisions" / "Test Decision.md").exists()


def test_graph_health(project: Path):
    _reset_server_state(project)
    report = mcp_server.graph_health()
    assert report["total_nodes"] == 2
    assert report["broken_links"] == []


def test_reindex_picks_up_new_note(project: Path):
    _reset_server_state(project)
    # Initial state: 2 notes
    pre = mcp_server.graph_health()
    assert pre["total_nodes"] == 2
    # Add a new note
    (project / "cma" / "vault" / "004-patterns" / "New Pattern.md").write_text(
        "---\ntype: pattern\ntitle: New Pattern\n---\n\nA fresh idea.\n",
        encoding="utf-8",
    )
    # Before reindex, the server still sees 2
    mid = mcp_server.graph_health()
    assert mid["total_nodes"] == 2
    # After reindex, 3
    rebuild = mcp_server.reindex()
    assert rebuild["status"] == "rebuilt"
    post = mcp_server.graph_health()
    assert post["total_nodes"] == 3

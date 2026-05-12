"""Tests for the Claude Code hook entry points (UserPromptSubmit and Stop)."""

import io
import json
import sys
from pathlib import Path

from cma.hooks import (
    _capture_prompt_to_inbox,
    _quick_retrieve,
    stop_hook,
    user_prompt_hook,
)


def _project(tmp_path: Path) -> Path:
    """Bare CMA project layout for testing hooks."""
    project = tmp_path / "agent"
    (project / "cma" / "vault" / "000-inbox").mkdir(parents=True)
    (project / "cma" / "vault" / "002-sessions").mkdir(parents=True)
    (project / "cma" / "vault" / "003-decisions").mkdir(parents=True)
    (project / "cma" / "memory_log").mkdir(parents=True)
    (project / "cma" / "config.yaml").write_text(
        "vault_path: ./cma/vault\nindex_path: ./cma/cache\nembedding_provider: none\n",
        encoding="utf-8",
    )
    return project


def test_capture_prompt_writes_inbox_note(tmp_path: Path):
    project = _project(tmp_path)
    path = _capture_prompt_to_inbox(project, "What about classifier confidence?", "sess-001")

    assert path.exists()
    assert "000-inbox/prompts" in path.as_posix()
    body = path.read_text(encoding="utf-8")
    assert "type: prompt" in body
    assert "status: noise" in body
    assert "session_id: sess-001" in body
    assert "What about classifier confidence?" in body


def test_quick_retrieve_returns_real_context_spec_with_fragments(tmp_path: Path):
    """The hook runs the FULL Retriever pipeline (BM25-only seeds) and returns
    a rendered Context Spec with actual fragments, not just titles. This is the
    whole point of the Retriever (whitepaper §4): hand the agent the relevant
    CHUNKS, not the raw note bodies for the agent to re-read."""
    project = _project(tmp_path)
    (project / "cma" / "vault" / "003-decisions" / "Classifier Confidence Bands.md").write_text(
        "---\ntype: decision\ntitle: Classifier Confidence Bands\nstatus: accepted\n---\n\n"
        "We use three confidence bands for the classifier output: above 0.85 is "
        "high-confidence, between 0.55 and 0.85 is tentative, below 0.55 routes to digest.\n"
        "The 0.55 floor was tuned empirically; below it, accuracy drops under 70%.\n",
        encoding="utf-8",
    )

    context, spec_id, source_artifacts = _quick_retrieve(project, "classifier confidence")

    assert context is not None
    assert spec_id is not None
    # Real Context Spec has these sections, not just a list of titles
    assert "Context Spec" in context or "Fragments" in context
    assert "Classifier Confidence Bands" in context
    # The fragment text should be embedded, not just the title
    assert "three confidence bands" in context.lower() or "0.55" in context

    # And the spec should have been PERSISTED to the vault (GraphRAG flywheel)
    spec_path = project / "cma" / "vault" / "008-context-specs" / f"{spec_id}.md"
    assert spec_path.exists()

    # Per-source artifacts populated with token info
    assert source_artifacts is not None
    assert len(source_artifacts) >= 1
    a = source_artifacts[0]
    assert a["title"] == "Classifier Confidence Bands"
    assert a["tokens_extracted"] > 0
    assert a["tokens_total"] > 0
    assert 0 < a["percent"] <= 100


def test_quick_retrieve_returns_none_on_empty_vault(tmp_path: Path):
    project = _project(tmp_path)
    context, spec_id, source_artifacts = _quick_retrieve(project, "anything")
    assert context is None
    assert spec_id is None
    assert source_artifacts is None


def test_quick_retrieve_handles_no_matches_gracefully(tmp_path: Path):
    """When the vault has notes but none match the query, return a tiny breadcrumb
    so the agent knows the retrieve ran but found nothing useful."""
    project = _project(tmp_path)
    (project / "cma" / "vault" / "003-decisions" / "Async Queue.md").write_text(
        "---\ntype: decision\ntitle: Async Queue\nstatus: accepted\n---\n\n"
        "Move processing to an async queue for throughput.\n",
        encoding="utf-8",
    )

    context, spec_id, source_artifacts = _quick_retrieve(
        project, "completely unrelated quantum chromodynamics"
    )

    # We got SOMETHING (a spec was created), even if there were no fragments above threshold.
    # The spec_id is still useful for the dashboard to link to.
    assert context is not None
    assert spec_id is not None
    # No fragments => no source artifacts (empty list)
    assert source_artifacts == [] or source_artifacts is None


def test_user_prompt_hook_writes_inbox_and_outputs_context(tmp_path: Path, monkeypatch, capsys):
    project = _project(tmp_path)
    (project / "cma" / "vault" / "003-decisions" / "Async Queue Decision.md").write_text(
        "---\ntype: decision\ntitle: Async Queue Decision\nstatus: accepted\n---\n\n"
        "Move capital call processing to an async queue.\n",
        encoding="utf-8",
    )

    payload = {
        "session_id": "test-session-001",
        "cwd": str(project),
        "prompt": "What did we decide about the async queue?",
        "hook_event_name": "UserPromptSubmit",
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    exit_code = user_prompt_hook()
    out = capsys.readouterr().out

    assert exit_code == 0
    # Real Context Spec output, not just a title list
    assert "Context Spec" in out or "Async Queue Decision" in out

    # Inbox capture
    inbox_files = list((project / "cma" / "vault" / "000-inbox" / "prompts").rglob("*.md"))
    assert len(inbox_files) == 1
    assert "async queue" in inbox_files[0].read_text(encoding="utf-8").lower()

    # The retrieve persisted a spec note
    specs = list((project / "cma" / "vault" / "008-context-specs").glob("spec-*.md"))
    assert len(specs) >= 1


def test_user_prompt_hook_handles_missing_project_gracefully(tmp_path: Path, monkeypatch, capsys):
    # cwd has no CMA project; hook must not crash, must return 0, must produce no output
    payload = {"cwd": str(tmp_path), "prompt": "anything"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    exit_code = user_prompt_hook()
    out = capsys.readouterr().out

    assert exit_code == 0
    assert out == ""


def test_user_prompt_hook_handles_bad_input(monkeypatch, capsys):
    """Garbage stdin must not crash the hook -- it would silently break every user prompt."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("not valid json"))
    exit_code = user_prompt_hook()
    assert exit_code == 0


def test_stop_hook_appends_session_note(tmp_path: Path, monkeypatch):
    project = _project(tmp_path)
    payload = {
        "session_id": "test-session-stop-001",
        "cwd": str(project),
        "transcript_path": "/tmp/transcript.jsonl",
        "hook_event_name": "Stop",
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    exit_code = stop_hook()

    assert exit_code == 0
    session_path = project / "cma" / "vault" / "002-sessions" / "test-session-stop-001.md"
    assert session_path.exists()
    body = session_path.read_text(encoding="utf-8")
    assert "type: session" in body
    assert "Stop event" in body


def test_stop_hook_idempotent_appends(tmp_path: Path, monkeypatch):
    project = _project(tmp_path)
    payload = {"session_id": "sess-x", "cwd": str(project), "transcript_path": ""}

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    stop_hook()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    stop_hook()

    session_path = project / "cma" / "vault" / "002-sessions" / "sess-x.md"
    body = session_path.read_text(encoding="utf-8")
    # Header written once, two Stop event lines
    assert body.count("type: session") == 1
    assert body.count("Stop event") == 2


def test_hooks_log_to_activity(tmp_path: Path, monkeypatch):
    project = _project(tmp_path)
    payload = {"session_id": "act-test", "cwd": str(project), "prompt": "hello memory"}

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    user_prompt_hook()

    from cma.activity import read_events
    events = read_events(project)
    assert any(e.get("type") == "prompt" for e in events)
    prompt_event = next(e for e in events if e.get("type") == "prompt")
    assert prompt_event["summary"] == "hello memory"

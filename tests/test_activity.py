"""Tests for the activity logger and dashboard renderer."""

import json
from pathlib import Path

from cma.activity import (
    log_activity,
    read_events,
    render_dashboard_html,
)


def _project(tmp_path: Path) -> Path:
    """Minimal CMA project layout."""
    project = tmp_path / "agent"
    (project / "cma" / "memory_log").mkdir(parents=True)
    (project / "cma" / "vault").mkdir(parents=True)
    return project


def test_log_activity_creates_jsonl(tmp_path: Path):
    project = _project(tmp_path)
    log_activity(project, "search", query="capital calls", summary='"capital calls" -> 3 hits')

    log = project / "cma" / "memory_log" / "activity.jsonl"
    assert log.exists()
    lines = log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["type"] == "search"
    assert event["query"] == "capital calls"
    assert "ts" in event
    assert "session_id" in event


def test_log_activity_appends_multiple(tmp_path: Path):
    project = _project(tmp_path)
    log_activity(project, "search", query="alpha")
    log_activity(project, "retrieve", query="beta", duration_ms=1234.5)
    log_activity(project, "record", task_id="task-001", summary="recorded 2 decisions")

    events = read_events(project)
    assert len(events) == 3
    assert [e["type"] for e in events] == ["search", "retrieve", "record"]
    assert events[1]["duration_ms"] == 1234.5


def test_log_activity_writes_dashboard(tmp_path: Path):
    project = _project(tmp_path)
    log_activity(project, "retrieve", query="x", summary='"x" -> 1 source')

    dashboard = project / "cma" / "memory_log" / "dashboard.html"
    assert dashboard.exists()
    html = dashboard.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "CMA Memory Log" in html
    # Event payload is inlined as JSON in the page
    assert '"retrieve"' in html
    assert '"x"' in html


def test_log_activity_with_artifacts(tmp_path: Path):
    project = _project(tmp_path)
    log_activity(
        project, "record",
        task_id="task-002",
        summary="task: task-002 -> 1 written",
        artifacts=[
            {"title": "Move to async queue", "path": "003-decisions/Move to async queue.md", "kind": "decision"},
            {"title": "task-002", "path": "002-sessions/task-002.md", "kind": "session"},
        ],
    )

    events = read_events(project)
    assert len(events) == 1
    assert events[0]["artifacts"][0]["kind"] == "decision"
    assert events[0]["artifacts"][1]["kind"] == "session"


def test_log_activity_swallows_errors(tmp_path: Path):
    """Logging must never fail the host operation, even if the project is broken."""
    bogus = tmp_path / "no-such-project" / "with-no-cma-folder"
    # Should not raise
    log_activity(bogus, "search", query="x")


def test_read_events_empty_when_no_log(tmp_path: Path):
    project = _project(tmp_path)
    assert read_events(project) == []


def test_render_dashboard_html_inlines_events(tmp_path: Path):
    project = _project(tmp_path)
    events = [
        {
            "ts": "2026-05-09T18:42:11Z",
            "session_id": "20260509-184211-pid1",
            "type": "retrieve",
            "query": "notification routing",
            "summary": '"notification routing" -> 5 sources',
            "duration_ms": 1240.0,
            "artifacts": [
                {"title": "spec-9a3f1b2c", "path": "008-context-specs/spec-9a3f1b2c.md", "kind": "spec"},
            ],
        },
    ]
    html = render_dashboard_html(events, project)
    assert "<!DOCTYPE html>" in html
    assert "agent" in html  # project name
    assert "notification routing" in html
    assert "spec-9a3f1b2c" in html
    # Auto-refresh meta tag is present
    assert 'http-equiv="refresh"' in html
    # The events JSON is inlined safely (no </script> escape risk)
    assert "</script" not in html.split('id="payload">')[1].split("</script>")[0]


def test_render_dashboard_html_empty_state(tmp_path: Path):
    project = _project(tmp_path)
    html = render_dashboard_html([], project)
    # Empty state still renders valid HTML; the JS shows the empty message
    assert "<!DOCTYPE html>" in html
    assert '"events": []' in html or '"events":[]' in html


def test_session_id_stable_within_process(tmp_path: Path):
    """Two events from the same Python process share a session_id."""
    project = _project(tmp_path)
    log_activity(project, "search", query="a")
    log_activity(project, "search", query="b")
    events = read_events(project)
    assert events[0]["session_id"] == events[1]["session_id"]


def test_dashboard_re_rendered_on_each_event(tmp_path: Path):
    """Dashboard reflects the latest event count after each log_activity call."""
    project = _project(tmp_path)
    dashboard = project / "cma" / "memory_log" / "dashboard.html"

    log_activity(project, "search", query="alpha")
    html_after_one = dashboard.read_text(encoding="utf-8")

    log_activity(project, "retrieve", query="beta")
    html_after_two = dashboard.read_text(encoding="utf-8")

    assert html_after_one != html_after_two
    assert html_after_two.count('"type":') >= 2


def test_session_id_override_groups_events(tmp_path: Path):
    """When session_id is passed explicitly (e.g. from a hook), it overrides the
    per-process default so events from short-lived hook processes group with the
    actual Claude Code session."""
    project = _project(tmp_path)
    claude_session = "87aee6fc-cba9-4def-8acd-deadbeefcafe"

    log_activity(project, "prompt", summary="hi", session_id=claude_session)
    log_activity(project, "stop", summary="bye", session_id=claude_session)

    events = read_events(project)
    assert len(events) == 2
    assert events[0]["session_id"] == claude_session
    assert events[1]["session_id"] == claude_session


def test_session_id_default_when_not_overridden(tmp_path: Path):
    """Without an explicit session_id, log_activity uses the process-level default."""
    project = _project(tmp_path)
    log_activity(project, "search", query="x")
    events = read_events(project)
    assert events[0]["session_id"].startswith("20")  # YYYYMMDD- prefix

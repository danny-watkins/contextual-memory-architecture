"""Activity logging for real-life verification.

Every meaningful CMA operation (search, retrieve, record, index, ingest)
appends a JSON line to <project>/cma/memory_log/activity.jsonl AND triggers
a regeneration of <project>/cma/memory_log/dashboard.html. The dashboard
is a self-contained HTML file with auto-refresh: open it once in any
browser and watch the agent work in real time.

Design choices:
- JSONL (not SQLite) so the file is human-readable, gitignorable, and
  easy to cat or grep when debugging.
- Static HTML (not a server) so each agent's memory log is independent
  and works offline. Regeneration is cheap (~10ms per event).
- Meta-refresh (not WebSockets) so the page stays current with no extra
  process to run.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Per-process session id, generated lazily on first event.
_SESSION_ID: str | None = None


def _session_id() -> str:
    """Stable id for the current MCP-server / CLI process lifetime."""
    global _SESSION_ID
    if _SESSION_ID is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        _SESSION_ID = f"{ts}-pid{os.getpid()}"
    return _SESSION_ID


def _memory_log_dir(project_path: Path) -> Path:
    return Path(project_path) / "cma" / "memory_log"


def _activity_path(project_path: Path) -> Path:
    return _memory_log_dir(project_path) / "activity.jsonl"


def _dashboard_path(project_path: Path) -> Path:
    return _memory_log_dir(project_path) / "dashboard.html"


def log_activity(
    project_path: Path,
    event_type: str,
    *,
    duration_ms: float | None = None,
    task_id: str | None = None,
    query: str | None = None,
    summary: str | None = None,
    artifacts: list[dict[str, str]] | None = None,
    details: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> None:
    """Append one event to activity.jsonl and regenerate dashboard.html.

    Best-effort: if the project layout is wrong (e.g. memory_log dir missing
    and can't be created), this swallows the error rather than failing the
    caller. Memory logging should never break a real operation.

    If `session_id` is provided (e.g. by hooks that receive Claude Code's
    session id in their stdin payload), it overrides the per-process default,
    so events from short-lived hook processes group with the actual Claude Code
    session instead of fragmenting into one tiny session per hook fire.
    """
    try:
        project_path = Path(project_path).resolve()
        log_dir = _memory_log_dir(project_path)
        log_dir.mkdir(parents=True, exist_ok=True)

        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id or _session_id(),
            "type": event_type,
        }
        if task_id is not None:
            event["task_id"] = task_id
        if duration_ms is not None:
            event["duration_ms"] = round(duration_ms, 1)
        if query is not None:
            event["query"] = query
        if summary is not None:
            event["summary"] = summary
        if artifacts:
            event["artifacts"] = artifacts
        if details:
            event["details"] = details

        with open(_activity_path(project_path), "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        events = read_events(project_path)
        html = render_dashboard_html(events, project_path)
        _dashboard_path(project_path).write_text(html, encoding="utf-8")
    except Exception:
        # Logging must never fail the host operation.
        return


def read_events(project_path: Path) -> list[dict[str, Any]]:
    """Return all events from activity.jsonl, oldest first. Empty list if no log."""
    path = _activity_path(Path(project_path))
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


# ---------- HTML rendering ----------


def _bundled_template() -> str:
    """Read the dashboard template that ships in the bundle."""
    template_path = Path(__file__).parent / "_bundle" / "memory_log" / "dashboard_template.html"
    return template_path.read_text(encoding="utf-8")


def render_dashboard_html(events: list[dict[str, Any]], project_path: Path) -> str:
    """Render the full dashboard HTML with embedded event data."""
    project_name = Path(project_path).name
    vault_name = project_name  # Obsidian uses the vault folder name; here that's the project root
    payload = {
        "project_name": project_name,
        "vault_name": vault_name,
        "vault_path": str(Path(project_path) / "cma" / "vault"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events": events,
    }
    template = _bundled_template()
    # JSON.stringify-safe inlining
    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_json = payload_json.replace("</", "<\\/")
    return template.replace("{{PAYLOAD_JSON}}", payload_json)

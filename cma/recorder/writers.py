"""File writers for the four note types. All writes are idempotent-friendly:
duplicates are detected and skipped rather than overwritten.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

from cma.recorder.templates import (
    render_daily_log_entry,
    render_daily_log_header,
    render_decision,
    render_pattern,
    render_session,
)
from cma.schemas.completion_package import CompletionPackage, Decision, Pattern

ILLEGAL_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def sanitize_filename(title: str) -> str:
    """Convert a free-text title into a filename safe on Windows and POSIX.

    Strips path separators, control chars, and trims length.
    """
    cleaned = ILLEGAL_FS_CHARS.sub("-", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-")
    return cleaned[:100] if cleaned else "untitled"


def write_session(
    vault_path: Path,
    package: CompletionPackage,
    decision_titles: list[str],
    pattern_titles: list[str],
) -> Path:
    sessions_dir = Path(vault_path) / "002-sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{sanitize_filename(package.task_id)}.md"
    path.write_text(
        render_session(package, decision_titles, pattern_titles), encoding="utf-8"
    )
    return path


def write_decision(
    vault_path: Path,
    decision: Decision,
    package: CompletionPackage,
    *,
    status_override: str | None = None,
    proposal_dir: Path | None = None,
    related_titles: list[str] | None = None,
) -> tuple[Path | None, str]:
    """Write a decision note. Returns (path, status_label).

    If `proposal_dir` is provided, writes there instead of the vault. If a file
    with the same title already exists in the vault decisions folder, returns
    (None, "duplicate") without overwriting.
    """
    rendered = render_decision(
        decision, package,
        status_override=status_override,
        related_titles=related_titles,
    )
    if proposal_dir is not None:
        proposal_dir.mkdir(parents=True, exist_ok=True)
        path = proposal_dir / f"{sanitize_filename(decision.title)}.md"
        path.write_text(rendered, encoding="utf-8")
        return path, "proposed"

    decisions_dir = Path(vault_path) / "003-decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    path = decisions_dir / f"{sanitize_filename(decision.title)}.md"
    if path.exists():
        return None, "duplicate"
    path.write_text(rendered, encoding="utf-8")
    return path, "written"


def write_pattern(
    vault_path: Path,
    pattern: Pattern,
    package: CompletionPackage,
    *,
    status_override: str | None = None,
    proposal_dir: Path | None = None,
    related_titles: list[str] | None = None,
) -> tuple[Path | None, str]:
    """Write a pattern note. Returns (path, status_label)."""
    rendered = render_pattern(
        pattern, package,
        status_override=status_override,
        related_titles=related_titles,
    )
    if proposal_dir is not None:
        proposal_dir.mkdir(parents=True, exist_ok=True)
        path = proposal_dir / f"{sanitize_filename(pattern.title)}.md"
        path.write_text(rendered, encoding="utf-8")
        return path, "proposed"

    patterns_dir = Path(vault_path) / "004-patterns"
    patterns_dir.mkdir(parents=True, exist_ok=True)
    path = patterns_dir / f"{sanitize_filename(pattern.title)}.md"
    if path.exists():
        return None, "duplicate"
    path.write_text(rendered, encoding="utf-8")
    return path, "written"


def append_daily_log(
    vault_path: Path,
    package: CompletionPackage,
    today: date | None = None,
) -> Path:
    """Append a one-paragraph entry to today's daily log. Creates the file if missing."""
    today = today or datetime.now(timezone.utc).date()
    daily_dir = Path(vault_path) / "010-daily-log"
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{today.isoformat()}.md"
    entry = render_daily_log_entry(package)

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        # Skip if this task has already been logged today
        if f"## {package.task_id}:" in existing:
            return path
        path.write_text(existing.rstrip() + "\n\n" + entry, encoding="utf-8")
    else:
        path.write_text(render_daily_log_header(today) + entry, encoding="utf-8")
    return path

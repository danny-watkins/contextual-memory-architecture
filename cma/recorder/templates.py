"""Markdown templates for the four note types the Recorder writes."""

from __future__ import annotations

from datetime import date, datetime, timezone

import yaml

from cma.schemas.completion_package import CompletionPackage, Decision, Pattern


def _frontmatter(fm: dict) -> str:
    return "---\n" + yaml.safe_dump(fm, sort_keys=False, default_flow_style=False).strip() + "\n---"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def render_session(
    package: CompletionPackage,
    decision_titles: list[str],
    pattern_titles: list[str],
) -> str:
    """A session note records what happened on a single task.

    Always written (every CompletionPackage produces exactly one session note).
    Links to every decision/pattern recorded from the same task.
    """
    fm = {
        "type": "session",
        "title": f"{package.task_id}: {package.goal[:60]}",
        "task_id": package.task_id,
        "created": _now_iso(),
        "status": "active",
    }

    lines = [_frontmatter(fm), "", f"# {package.task_id}", ""]
    lines += ["## Goal", package.goal, ""]
    lines += ["## Summary", package.summary, ""]

    if package.outputs:
        lines.append("## Outputs")
        for o in package.outputs:
            lines.append(f"- {o}")
        lines.append("")

    if decision_titles:
        lines.append("## Decisions")
        for title in decision_titles:
            lines.append(f"- [[{title}]]")
        lines.append("")

    if pattern_titles:
        lines.append("## Patterns observed")
        for title in pattern_titles:
            lines.append(f"- [[{title}]]")
        lines.append("")

    cu = package.context_usage
    if cu.high_value or cu.low_value or cu.missing:
        lines.append("## Context usage")
        if cu.high_value:
            lines.append(f"**High value:** {', '.join(cu.high_value)}")
        if cu.low_value:
            lines.append(f"**Low value:** {', '.join(cu.low_value)}")
        if cu.missing:
            lines.append(f"**Missing:** {', '.join(cu.missing)}")
        lines.append("")

    if package.human_feedback:
        lines += ["## Human feedback", package.human_feedback, ""]

    return "\n".join(lines).rstrip() + "\n"


def render_decision(
    decision: Decision,
    package: CompletionPackage,
    status_override: str | None = None,
) -> str:
    fm = {
        "type": "decision",
        "title": decision.title,
        "task_id": package.task_id,
        "status": status_override or decision.status,
        "confidence": decision.confidence,
        "created": _now_iso(),
        "human_verified": False,
    }
    lines = [_frontmatter(fm), "", f"# {decision.title}", ""]
    if decision.rationale:
        lines += ["## Rationale", decision.rationale, ""]
    lines.append(f"Recorded from [[{package.task_id}]].")
    return "\n".join(lines).rstrip() + "\n"


def render_pattern(
    pattern: Pattern,
    package: CompletionPackage,
    status_override: str | None = None,
) -> str:
    fm = {
        "type": "pattern",
        "title": pattern.title,
        "task_id": package.task_id,
        "status": status_override or "active",
        "confidence": pattern.confidence,
        "created": _now_iso(),
    }
    lines = [_frontmatter(fm), "", f"# {pattern.title}", ""]
    if pattern.evidence:
        lines.append("## Evidence")
        for ev in pattern.evidence:
            lines.append(f"- {ev}")
        lines.append("")
    lines.append(f"First observed in [[{package.task_id}]].")
    return "\n".join(lines).rstrip() + "\n"


def render_daily_log_entry(package: CompletionPackage) -> str:
    """A single entry appended to the daily log file."""
    return (
        f"## {package.task_id}: {package.goal[:80]}\n"
        f"- summary: {package.summary}\n"
        f"- decisions: {len(package.decisions)}\n"
        f"- patterns: {len(package.patterns)}\n"
        f"- session: [[{package.task_id}]]\n"
    )


def render_daily_log_header(today: date) -> str:
    fm = {
        "type": "daily_log",
        "title": f"{today.isoformat()} Daily Log",
        "created": today.isoformat(),
        "status": "active",
    }
    return _frontmatter(fm) + f"\n\n# {today.isoformat()}\n\n"

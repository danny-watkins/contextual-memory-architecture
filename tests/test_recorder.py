from pathlib import Path

import pytest

from cma.config import RecorderConfig
from cma.recorder import (
    Recorder,
    WriteDecision,
    policy_for_decision,
    policy_for_pattern,
    sanitize_filename,
)
from cma.schemas.completion_package import (
    CompletionPackage,
    ContextUsage,
    Decision,
    Pattern,
)


def _package(decisions=None, patterns=None) -> CompletionPackage:
    return CompletionPackage(
        task_id="CMA-2026-0001",
        goal="Diagnose slow capital call processing",
        summary="Found a synchronous fund-admin API call in the hot path.",
        outputs=["proposed move to async queue"],
        decisions=decisions or [],
        patterns=patterns or [],
        context_usage=ContextUsage(
            high_value=["Capital Call Processing ADR"],
            low_value=["Old Fund Admin Migration Notes"],
            missing=[],
        ),
        human_feedback="confirmed by Danny",
    )


# ---------- policy ----------


def test_policy_decision_below_floor_skips():
    cfg = RecorderConfig()
    d = Decision(title="x", confidence=0.10, status="proposed")
    action, _ = policy_for_decision(d, cfg)
    assert action == WriteDecision.SKIP


def test_policy_accepted_decision_writes():
    cfg = RecorderConfig()
    d = Decision(title="x", confidence=0.30, status="accepted")
    action, _ = policy_for_decision(d, cfg)
    assert action == WriteDecision.WRITE


def test_policy_rejected_decision_writes():
    cfg = RecorderConfig()
    d = Decision(title="x", confidence=0.40, status="rejected")
    action, _ = policy_for_decision(d, cfg)
    assert action == WriteDecision.WRITE


def test_policy_high_confidence_proposed_writes():
    cfg = RecorderConfig()
    d = Decision(title="x", confidence=0.80, status="proposed")
    action, _ = policy_for_decision(d, cfg)
    assert action == WriteDecision.WRITE


def test_policy_tentative_proposed_drafts():
    cfg = RecorderConfig()
    d = Decision(title="x", confidence=0.60, status="proposed")
    action, _ = policy_for_decision(d, cfg)
    assert action == WriteDecision.DRAFT


def test_policy_weak_proposed_proposes():
    cfg = RecorderConfig()
    d = Decision(title="x", confidence=0.30, status="proposed")
    action, _ = policy_for_decision(d, cfg)
    assert action == WriteDecision.PROPOSE


def test_policy_supersede_requires_approval_when_configured():
    cfg = RecorderConfig(require_human_approval_for=["supersede_decision"])
    d = Decision(title="x", confidence=0.9, status="superseded")
    action, _ = policy_for_decision(d, cfg)
    assert action == WriteDecision.PROPOSE


def test_policy_pattern_below_floor_skips():
    cfg = RecorderConfig()
    p = Pattern(title="x", confidence=0.10)
    action, _ = policy_for_pattern(p, cfg)
    assert action == WriteDecision.SKIP


def test_policy_pattern_strong_writes():
    cfg = RecorderConfig()
    p = Pattern(title="x", confidence=0.85)
    action, _ = policy_for_pattern(p, cfg)
    assert action == WriteDecision.WRITE


def test_policy_pattern_tentative_drafts_when_no_approval_required():
    cfg = RecorderConfig(require_human_approval_for=[])
    p = Pattern(title="x", confidence=0.60)
    action, _ = policy_for_pattern(p, cfg)
    assert action == WriteDecision.DRAFT


def test_policy_pattern_tentative_proposes_when_approval_required():
    cfg = RecorderConfig(require_human_approval_for=["low_confidence_pattern"])
    p = Pattern(title="x", confidence=0.60)
    action, _ = policy_for_pattern(p, cfg)
    assert action == WriteDecision.PROPOSE


# ---------- writers / e2e ----------


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "agent"
    (project / "vault").mkdir(parents=True)
    (project / "cma" / "memory_log" / "proposals").mkdir(parents=True)
    (project / "cma" / "memory_log" / "write_logs").mkdir(parents=True)
    return project


def test_record_writes_session_and_daily_log(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
        write_logs_path=project / "cma" / "memory_log" / "write_logs",
    )
    package = _package()
    result = recorder.record_completion(package)

    session_path = project / "vault" / "002-sessions" / "CMA-2026-0001.md"
    assert session_path.exists()
    assert session_path in result.written

    # Daily log
    daily = list((project / "vault" / "010-daily-log").glob("*.md"))
    assert len(daily) == 1
    assert "CMA-2026-0001" in daily[0].read_text(encoding="utf-8")


def test_record_writes_accepted_decision(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )
    package = _package(
        decisions=[
            Decision(
                title="Move capital call processing to async queue",
                status="accepted",
                confidence=0.86,
                rationale="Synchronous calls cap latency at fund-admin API.",
            )
        ]
    )
    result = recorder.record_completion(package)
    decision_path = (
        project
        / "vault"
        / "003-decisions"
        / "Move capital call processing to async queue.md"
    )
    assert decision_path.exists()
    assert decision_path in result.written
    content = decision_path.read_text(encoding="utf-8")
    assert "type: decision" in content
    assert "status: accepted" in content
    assert "confidence: 0.86" in content
    assert "[[CMA-2026-0001]]" in content


def test_record_skips_low_confidence_pattern(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )
    package = _package(
        patterns=[Pattern(title="weak hunch", confidence=0.15)],
    )
    result = recorder.record_completion(package)
    assert any("pattern: weak hunch" in label for label, _ in result.skipped)
    assert not (project / "vault" / "004-patterns" / "weak hunch.md").exists()


def test_record_proposes_weak_decision(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )
    package = _package(
        decisions=[
            Decision(title="weak proposal", confidence=0.30, status="proposed"),
        ]
    )
    result = recorder.record_completion(package)
    proposal_path = (
        project
        / "cma"
        / "memory_log"
        / "proposals"
        / "decisions"
        / "weak proposal.md"
    )
    assert proposal_path.exists()
    assert proposal_path in result.proposed
    # Should NOT be in vault
    assert not (project / "cma" / "vault" / "003-decisions" / "weak proposal.md").exists()


def test_record_skips_duplicate_decision(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )
    package = _package(
        decisions=[Decision(title="dup", status="accepted", confidence=0.9)]
    )
    recorder.record_completion(package)
    # Second time should detect duplicate
    result = recorder.record_completion(package)
    assert any("duplicate" in reason for _, reason in result.skipped)


def test_record_dry_run_writes_nothing(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )
    package = _package(
        decisions=[Decision(title="dry one", status="accepted", confidence=0.9)],
    )
    result = recorder.record_completion(package, dry_run=True)
    # Items reported as "would write" but no files created
    assert result.written
    assert not (project / "vault" / "003-decisions" / "dry one.md").exists()
    assert not (project / "vault" / "002-sessions" / "CMA-2026-0001.md").exists()


def test_record_drafts_tentative_pattern(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
        config=RecorderConfig(require_human_approval_for=[]),
    )
    package = _package(
        patterns=[Pattern(title="tentative idea", confidence=0.60)],
    )
    recorder.record_completion(package)
    path = project / "vault" / "004-patterns" / "tentative idea.md"
    assert path.exists()
    assert "status: draft" in path.read_text(encoding="utf-8")


def test_record_links_decisions_in_session_note(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )
    package = _package(
        decisions=[
            Decision(title="dec one", status="accepted", confidence=0.9),
            Decision(title="dec two", status="accepted", confidence=0.9),
        ]
    )
    recorder.record_completion(package)
    session = (project / "vault" / "002-sessions" / "CMA-2026-0001.md").read_text(
        encoding="utf-8"
    )
    assert "[[dec one]]" in session
    assert "[[dec two]]" in session


def test_load_completion_package_yaml(tmp_path: Path):
    yaml_path = tmp_path / "pkg.yaml"
    yaml_path.write_text(
        """
task_id: CMA-2026-0001
goal: test goal
summary: test summary
decisions:
  - title: My decision
    status: accepted
    confidence: 0.9
    rationale: because
""",
        encoding="utf-8",
    )
    pkg = Recorder.load_completion_package(yaml_path)
    assert pkg.task_id == "CMA-2026-0001"
    assert len(pkg.decisions) == 1
    assert pkg.decisions[0].title == "My decision"


# ---------- filename sanitization ----------


def test_sanitize_filename_strips_path_separators():
    assert sanitize_filename("foo/bar:baz") == "foo-bar-baz"


def test_sanitize_filename_collapses_whitespace():
    assert sanitize_filename("foo   bar baz") == "foo bar baz"


def test_sanitize_filename_replaces_control_chars():
    assert sanitize_filename("foo\nbar\tbaz") == "foo-bar-baz"


def test_sanitize_filename_handles_empty():
    assert sanitize_filename("") == "untitled"
    assert sanitize_filename("   ") == "untitled"


def test_sanitize_filename_truncates_long_titles():
    long = "a" * 500
    assert len(sanitize_filename(long)) == 100


# ---------- auto-related links ----------


def test_decision_with_no_existing_notes_has_no_related_section(tmp_path: Path):
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )
    package = _package(
        decisions=[
            Decision(
                title="Move capital call processing to async queue",
                status="accepted",
                confidence=0.86,
                rationale="Synchronous calls cap latency at fund-admin API.",
            )
        ]
    )
    recorder.record_completion(package)
    decision_text = (project / "vault" / "003-decisions" /
                     "Move capital call processing to async queue.md").read_text(encoding="utf-8")
    assert "## Related" not in decision_text


def test_second_related_decision_links_to_first(tmp_path: Path):
    """When a new decision overlaps with an existing one, the new note should link to the existing one."""
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )

    first = _package(
        decisions=[
            Decision(
                title="Move capital call processing to async queue",
                status="accepted",
                confidence=0.9,
                rationale="Sync fund-admin API calls dominate capital call latency.",
            )
        ]
    )
    recorder.record_completion(first)

    second = CompletionPackage(
        task_id="CMA-2026-0002",
        goal="Pick a queue backend for the async capital call work",
        summary="Selected Redis Streams over RabbitMQ.",
        decisions=[
            Decision(
                title="Use Redis Streams for capital call queue",
                status="accepted",
                confidence=0.85,
                rationale="Capital call queue needs ordering and replay; Redis Streams gives both.",
            )
        ],
        context_usage=ContextUsage(),
    )
    recorder.record_completion(second)

    new_text = (project / "vault" / "003-decisions" /
                "Use Redis Streams for capital call queue.md").read_text(encoding="utf-8")
    assert "## Related" in new_text
    assert "[[Move capital call processing to async queue]]" in new_text


def test_unrelated_decision_does_not_get_spurious_links(tmp_path: Path):
    """A new decision on an unrelated topic should not link to the existing one."""
    project = _project(tmp_path)
    recorder = Recorder(
        vault_path=project / "vault",
        proposals_path=project / "cma" / "memory_log" / "proposals",
    )

    first = _package(
        decisions=[
            Decision(
                title="Move capital call processing to async queue",
                status="accepted",
                confidence=0.9,
                rationale="Sync fund-admin API calls dominate capital call latency.",
            )
        ]
    )
    recorder.record_completion(first)

    second = CompletionPackage(
        task_id="CMA-2026-0003",
        goal="Pick a logging library for the new web frontend",
        summary="Chose pino over winston.",
        decisions=[
            Decision(
                title="Use pino for frontend structured logging",
                status="accepted",
                confidence=0.8,
                rationale="Pino has lower overhead and better JSON output.",
            )
        ],
        context_usage=ContextUsage(),
    )
    recorder.record_completion(second)

    new_text = (project / "vault" / "003-decisions" /
                "Use pino for frontend structured logging.md").read_text(encoding="utf-8")
    assert "## Related" not in new_text

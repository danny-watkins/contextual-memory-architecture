from datetime import datetime

import pytest
from pydantic import ValidationError

from cma.schemas import (
    CompletionPackage,
    ContextRequest,
    ContextSpec,
    Decision,
    Fragment,
    MemoryRecord,
    TaskFrame,
)


def test_task_frame_minimal():
    tf = TaskFrame(
        task_id="CMA-2026-0001",
        goal="diagnose slow capital call processing",
        context_request=ContextRequest(query="capital call processing"),
    )
    assert tf.risk_level == "medium"
    assert tf.requires_memory is True
    assert tf.context_request.max_depth == 2


def test_task_frame_rejects_invalid_risk():
    with pytest.raises(ValidationError):
        TaskFrame(
            task_id="t1",
            goal="g",
            context_request=ContextRequest(query="q"),
            risk_level="catastrophic",  # type: ignore[arg-type]
        )


def test_context_spec_with_fragments():
    spec = ContextSpec(
        spec_id="spec-1",
        task_id="CMA-2026-0001",
        query="capital call processing",
        generated_at=datetime(2026, 5, 4, 10, 0, 0),
        fragments=[
            Fragment(
                source_node="Capital Call ADR",
                node_type="decision",
                node_score=0.84,
                fragment_score=0.78,
                depth=0,
                text="Prior decision text...",
                why_included="defines current architecture",
            )
        ],
    )
    assert len(spec.fragments) == 1
    assert spec.fragments[0].node_score == 0.84


def test_completion_package_defaults():
    pkg = CompletionPackage(task_id="t1", goal="g", summary="s")
    assert pkg.context_usage.high_value == []
    assert pkg.decisions == []


def test_decision_status_validation():
    d = Decision(title="Test", status="accepted", confidence=0.9)
    assert d.status == "accepted"
    with pytest.raises(ValidationError):
        Decision(title="Test", status="maybe")  # type: ignore[arg-type]


def test_memory_record_defaults():
    rec = MemoryRecord(
        record_id="welcome",
        type="note",
        title="Welcome",
        path="000-inbox/Welcome.md",
    )
    assert rec.status == "active"
    assert rec.human_verified is False
    assert rec.tags == []

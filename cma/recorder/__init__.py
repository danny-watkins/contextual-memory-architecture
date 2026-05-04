"""Recorder - memory formation node.

Converts completed tasks (CompletionPackages) into structured durable memory:
session notes, decision notes, pattern notes, daily log entries. Honors the
memory write policy so low-confidence inferences don't pollute the vault.
"""

from cma.recorder.policy import (
    WriteDecision,
    policy_for_decision,
    policy_for_pattern,
)
from cma.recorder.recorder import Recorder, RecorderResult
from cma.recorder.templates import (
    render_daily_log_entry,
    render_decision,
    render_pattern,
    render_session,
)
from cma.recorder.writers import (
    append_daily_log,
    sanitize_filename,
    write_decision,
    write_pattern,
    write_session,
)

__all__ = [
    "Recorder",
    "RecorderResult",
    "WriteDecision",
    "policy_for_decision",
    "policy_for_pattern",
    "render_session",
    "render_decision",
    "render_pattern",
    "render_daily_log_entry",
    "write_session",
    "write_decision",
    "write_pattern",
    "append_daily_log",
    "sanitize_filename",
]

"""Memory write policy: decide whether each item in a CompletionPackage gets written.

Implements the whitepaper's three-tier policy:
  - Always write: accepted/rejected decisions, sessions, completed-task outputs
  - Maybe write (as draft or proposal): tentative patterns, low-confidence inferences
  - Do not write: trivial guesses below the confidence floor

Also honors `recorder.require_human_approval_for` so users can route specific
categories (autonomy_change, low_confidence_pattern, supersede_decision)
through the proposals folder instead of writing directly to the vault.
"""

from __future__ import annotations

from enum import Enum

from cma.config import RecorderConfig
from cma.schemas.completion_package import Decision, Pattern


class WriteDecision(str, Enum):
    """Outcome of running a CompletionPackage item through the policy."""

    WRITE = "write"      # write to the vault as active
    DRAFT = "draft"      # write to the vault but mark status=draft
    PROPOSE = "propose"  # write to recorder/memory_write_proposals/ for human review
    SKIP = "skip"        # do not write at all


CONFIDENCE_FLOOR = 0.25
CONFIDENCE_STRONG = 0.75
CONFIDENCE_TENTATIVE = 0.50


def policy_for_decision(
    decision: Decision, recorder_config: RecorderConfig
) -> tuple[WriteDecision, str]:
    """Return (action, reason) for a Decision.

    Status drives most outcomes:
      - accepted/rejected     -> WRITE (recorded for posterity, even rejected ones matter)
      - superseded            -> WRITE or PROPOSE (depending on config)
      - proposed + confidence -> WRITE / DRAFT / PROPOSE / SKIP based on confidence band
    """
    if decision.confidence < CONFIDENCE_FLOOR:
        return WriteDecision.SKIP, f"confidence {decision.confidence:.2f} below {CONFIDENCE_FLOOR}"

    if decision.status == "accepted":
        return WriteDecision.WRITE, "accepted decision"

    if decision.status == "rejected":
        return WriteDecision.WRITE, "rejected decision (recorded for future reference)"

    if decision.status == "superseded":
        if "supersede_decision" in recorder_config.require_human_approval_for:
            return WriteDecision.PROPOSE, "superseding requires human approval"
        return WriteDecision.WRITE, "superseded decision"

    # status == "proposed"
    if decision.confidence >= CONFIDENCE_STRONG:
        return WriteDecision.WRITE, "high-confidence proposed decision"
    if decision.confidence >= CONFIDENCE_TENTATIVE:
        return WriteDecision.DRAFT, "tentative proposed decision (saved as draft)"
    return WriteDecision.PROPOSE, "weak-signal proposed decision needs human approval"


def policy_for_pattern(
    pattern: Pattern, recorder_config: RecorderConfig
) -> tuple[WriteDecision, str]:
    """Return (action, reason) for a Pattern.

    Patterns are inferred (not human-stated) so they're held to a higher bar:
    only high-confidence patterns auto-write; medium-confidence go to drafts
    or proposals depending on config.
    """
    if pattern.confidence < CONFIDENCE_FLOOR:
        return WriteDecision.SKIP, f"confidence {pattern.confidence:.2f} below {CONFIDENCE_FLOOR}"

    if pattern.confidence >= CONFIDENCE_STRONG:
        return WriteDecision.WRITE, "strong-evidence pattern"

    if pattern.confidence >= CONFIDENCE_TENTATIVE:
        if "low_confidence_pattern" in recorder_config.require_human_approval_for:
            return WriteDecision.PROPOSE, "tentative pattern needs human approval"
        return WriteDecision.DRAFT, "tentative pattern (saved as draft)"

    return WriteDecision.PROPOSE, "weak-signal pattern needs human approval"

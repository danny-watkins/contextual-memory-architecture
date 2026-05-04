"""CompletionPackage: the structured handoff from Reasoner to Recorder after a task."""

from typing import Literal

from pydantic import BaseModel, Field


class Decision(BaseModel):
    title: str
    status: Literal["proposed", "accepted", "rejected", "superseded"] = "proposed"
    confidence: float = 0.5
    rationale: str = ""


class Pattern(BaseModel):
    title: str
    confidence: float = 0.5
    evidence: list[str] = Field(default_factory=list)


class ContextUsage(BaseModel):
    high_value: list[str] = Field(default_factory=list)
    low_value: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class CompletionPackage(BaseModel):
    task_id: str
    goal: str
    summary: str
    outputs: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)
    context_usage: ContextUsage = Field(default_factory=ContextUsage)
    human_feedback: str = ""

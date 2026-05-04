"""TaskFrame: the structured request the Reasoner emits to the Retriever."""

from typing import Literal

from pydantic import BaseModel, Field


class ContextRequest(BaseModel):
    query: str
    max_tokens: int = 8000
    max_depth: int = 2
    beam_width: int = 5
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class TaskFrame(BaseModel):
    task_id: str
    goal: str
    domain: str = "general"
    risk_level: Literal["low", "medium", "high"] = "medium"
    requires_memory: bool = True
    context_request: ContextRequest
    constraints: list[str] = Field(default_factory=list)
    expected_output: list[str] = Field(default_factory=list)

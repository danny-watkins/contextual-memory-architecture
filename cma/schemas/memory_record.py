"""MemoryRecord: the in-memory representation of a single vault note."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MEMORY_TYPES = (
    "session",
    "decision",
    "pattern",
    "postmortem",
    "daily_log",
    "profile",
    "report",
    "project",
    "person",
    "tool",
    "codebase",
    "context_spec",
    "note",
)

MemoryStatus = Literal[
    "draft",
    "active",
    "proposed",
    "accepted",
    "rejected",
    "superseded",
    "archived",
]
VALID_STATUSES = {
    "draft",
    "active",
    "proposed",
    "accepted",
    "rejected",
    "superseded",
    "archived",
}


class MemoryRecord(BaseModel):
    record_id: str
    type: str = "note"
    title: str
    path: str
    created_at: datetime | None = None
    task_id: str | None = None
    domain: str | None = None
    confidence: float | None = None
    status: MemoryStatus = "active"
    links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    human_verified: bool = False
    body: str = ""
    frontmatter: dict = Field(default_factory=dict)

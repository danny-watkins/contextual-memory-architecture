"""ContextSpec: the structured artifact returned by the Retriever."""

from datetime import datetime

from pydantic import BaseModel, Field


class Fragment(BaseModel):
    source_node: str
    node_type: str
    node_score: float
    fragment_score: float
    depth: int
    text: str
    why_included: str = ""


class RelationshipEdge(BaseModel):
    source: str
    target: str
    edge_type: str = "wikilink"


class Exclusion(BaseModel):
    node: str
    reason: str


class ContextSpec(BaseModel):
    spec_id: str
    task_id: str
    query: str
    generated_at: datetime
    retriever_version: str = "0.1.0"
    parameters: dict = Field(default_factory=dict)
    fragments: list[Fragment] = Field(default_factory=list)
    relationship_map: list[RelationshipEdge] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    exclusions: list[Exclusion] = Field(default_factory=list)

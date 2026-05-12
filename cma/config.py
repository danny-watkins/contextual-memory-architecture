"""Configuration loader for CMA projects."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    alpha: float = 0.7
    max_depth: int = 2
    beam_width: int = 5
    node_threshold: float = 0.30
    fragment_threshold: float = 0.42
    depth_decay: float = 0.80
    max_fragments_per_node: int = 3


class RecorderConfig(BaseModel):
    require_human_approval_for: list[str] = Field(
        default_factory=lambda: [
            "autonomy_change",
            "low_confidence_pattern",
            "supersede_decision",
        ]
    )
    default_confidence: float = 0.60


class CMAConfig(BaseModel):
    vault_path: str = "./cma/vault"
    index_path: str = "./cma/cache"
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "all-MiniLM-L6-v2"
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    recorder: RecorderConfig = Field(default_factory=RecorderConfig)

    @classmethod
    def from_file(cls, path: Path) -> "CMAConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    @classmethod
    def from_project(cls, project_path: Path) -> "CMAConfig":
        config_path = Path(project_path) / "cma" / "config.yaml"
        if config_path.exists():
            return cls.from_file(config_path)
        return cls()

    def resolve_paths(self, project_path: Path) -> "CMAConfig":
        """Return a copy with vault_path and index_path resolved against the project root."""
        project = Path(project_path).resolve()
        copy = self.model_copy()
        copy.vault_path = str((project / self.vault_path).resolve())
        copy.index_path = str((project / self.index_path).resolve())
        return copy

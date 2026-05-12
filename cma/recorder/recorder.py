"""Top-level Recorder: turn a CompletionPackage into vault writes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from cma.config import CMAConfig, RecorderConfig
from cma.recorder.policy import (
    WriteDecision,
    policy_for_decision,
    policy_for_pattern,
)
from cma.recorder.writers import (
    append_daily_log,
    write_decision,
    write_pattern,
    write_session,
)
from cma.schemas.completion_package import CompletionPackage


@dataclass
class RecorderResult:
    """Tally of what the Recorder did with a given CompletionPackage."""

    written: list[Path] = field(default_factory=list)
    proposed: list[Path] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"written={len(self.written)} "
            f"proposed={len(self.proposed)} "
            f"skipped={len(self.skipped)}"
        )


class Recorder:
    """Memory formation node: writes session/decision/pattern/daily-log notes."""

    def __init__(
        self,
        vault_path: Path,
        proposals_path: Path,
        write_logs_path: Path | None = None,
        config: RecorderConfig | None = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.proposals_path = Path(proposals_path)
        self.write_logs_path = Path(write_logs_path) if write_logs_path else None
        self.config = config or RecorderConfig()

    @classmethod
    def from_project(cls, project_path: Path) -> "Recorder":
        project_path = Path(project_path).resolve()
        config = CMAConfig.from_project(project_path).resolve_paths(project_path)
        return cls(
            vault_path=Path(config.vault_path),
            proposals_path=project_path / "cma" / "memory_log" / "proposals",
            write_logs_path=project_path / "cma" / "memory_log" / "write_logs",
            config=config.recorder,
        )

    @staticmethod
    def load_completion_package(path: Path) -> CompletionPackage:
        """Load a CompletionPackage from a YAML or JSON file."""
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            data = yaml.safe_load(text)
        return CompletionPackage(**data)

    # ----- internal -----

    def _build_related_finder(self):
        """Return a function (text, top_k=3, threshold=0.4) -> [title] over existing decisions/patterns.

        Returns a no-op function if the vault is missing or contains no decisions/patterns yet.
        """
        try:
            from cma.retriever.lexical import BM25Index
            from cma.storage.markdown_store import parse_vault
        except Exception:
            return lambda text, top_k=3, threshold=0.4: []

        if not self.vault_path.exists():
            return lambda text, top_k=3, threshold=0.4: []

        records = parse_vault(self.vault_path)
        existing = [r for r in records if r.type in ("decision", "pattern")]
        if not existing:
            return lambda text, top_k=3, threshold=0.4: []

        index = BM25Index(existing)
        title_by_id = {r.record_id: r.title for r in existing}

        def find_related(text: str, top_k: int = 3, threshold: float = 0.4) -> list[str]:
            results = index.search(text, top_k=top_k * 2)
            out: list[str] = []
            for record_id, score in results:
                if score < threshold:
                    continue
                title = title_by_id.get(record_id)
                if title:
                    out.append(title)
                if len(out) >= top_k:
                    break
            return out

        return find_related

    def _process_decisions(
        self,
        package: CompletionPackage,
        dry_run: bool,
        result: RecorderResult,
        find_related,
    ) -> list[str]:
        """Write decisions according to policy. Returns the titles linked from the session."""
        linked_titles: list[str] = []
        for decision in package.decisions:
            action, reason = policy_for_decision(decision, self.config)
            label = f"decision: {decision.title}"

            if action == WriteDecision.SKIP:
                result.skipped.append((label, reason))
                continue

            status_override = "draft" if action == WriteDecision.DRAFT else None

            if dry_run:
                marker = (
                    f"<would-propose: {decision.title}>"
                    if action == WriteDecision.PROPOSE
                    else f"<would-write: {decision.title}>"
                )
                target = result.proposed if action == WriteDecision.PROPOSE else result.written
                target.append(Path(marker))
                linked_titles.append(decision.title)
                continue

            proposal_dir = (
                self.proposals_path / "decisions"
                if action == WriteDecision.PROPOSE
                else None
            )
            related = find_related(
                f"{decision.title}\n{decision.rationale or ''}"
            )
            # Don't link a note to itself if a same-title note somehow exists
            related = [t for t in related if t != decision.title]
            path, status = write_decision(
                self.vault_path,
                decision,
                package,
                status_override=status_override,
                proposal_dir=proposal_dir,
                related_titles=related or None,
            )
            if path is None:
                result.skipped.append((label, status))
                continue
            if status == "proposed":
                result.proposed.append(path)
            else:
                result.written.append(path)
            linked_titles.append(decision.title)
        return linked_titles

    def _process_patterns(
        self,
        package: CompletionPackage,
        dry_run: bool,
        result: RecorderResult,
        find_related,
    ) -> list[str]:
        linked_titles: list[str] = []
        for pattern in package.patterns:
            action, reason = policy_for_pattern(pattern, self.config)
            label = f"pattern: {pattern.title}"

            if action == WriteDecision.SKIP:
                result.skipped.append((label, reason))
                continue

            status_override = "draft" if action == WriteDecision.DRAFT else None

            if dry_run:
                marker = (
                    f"<would-propose: {pattern.title}>"
                    if action == WriteDecision.PROPOSE
                    else f"<would-write: {pattern.title}>"
                )
                target = result.proposed if action == WriteDecision.PROPOSE else result.written
                target.append(Path(marker))
                linked_titles.append(pattern.title)
                continue

            proposal_dir = (
                self.proposals_path / "patterns"
                if action == WriteDecision.PROPOSE
                else None
            )
            evidence_text = "\n".join(pattern.evidence) if pattern.evidence else ""
            related = find_related(f"{pattern.title}\n{evidence_text}")
            related = [t for t in related if t != pattern.title]
            path, status = write_pattern(
                self.vault_path,
                pattern,
                package,
                status_override=status_override,
                proposal_dir=proposal_dir,
                related_titles=related or None,
            )
            if path is None:
                result.skipped.append((label, status))
                continue
            if status == "proposed":
                result.proposed.append(path)
            else:
                result.written.append(path)
            linked_titles.append(pattern.title)
        return linked_titles

    def _write_session_and_log(
        self,
        package: CompletionPackage,
        decision_titles: list[str],
        pattern_titles: list[str],
        dry_run: bool,
        result: RecorderResult,
    ) -> None:
        if dry_run:
            result.written.append(Path(f"<would-write session: {package.task_id}>"))
            result.written.append(Path("<would-append daily log>"))
            return
        session_path = write_session(
            self.vault_path, package, decision_titles, pattern_titles
        )
        result.written.append(session_path)
        daily_path = append_daily_log(self.vault_path, package)
        result.written.append(daily_path)

    def _write_log(self, package: CompletionPackage, result: RecorderResult) -> None:
        """Persist a JSONL log of what was written for this task."""
        if self.write_logs_path is None:
            return
        self.write_logs_path.mkdir(parents=True, exist_ok=True)
        log_path = self.write_logs_path / f"{package.task_id}-write-log.jsonl"
        records = []
        for p in result.written:
            records.append({"action": "write", "path": str(p)})
        for p in result.proposed:
            records.append({"action": "propose", "path": str(p)})
        for label, reason in result.skipped:
            records.append({"action": "skip", "item": label, "reason": reason})
        with open(log_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    # ----- public -----

    def record_completion(
        self, package: CompletionPackage, dry_run: bool = False
    ) -> RecorderResult:
        """Process a completion package end-to-end.

        Order of operations:
          1. Decisions (policy-gated, may write to vault or proposals)
          2. Patterns (policy-gated, same routing)
          3. Session note (always written, links to anything written above)
          4. Daily log entry (always appended)
          5. Write log (JSONL audit trail), unless dry_run
        """
        result = RecorderResult()
        # Build the related-title finder once over the current vault state.
        # Best-effort: returns no-op if vault empty or BM25 unavailable.
        find_related = self._build_related_finder()
        decision_titles = self._process_decisions(package, dry_run, result, find_related)
        pattern_titles = self._process_patterns(package, dry_run, result, find_related)
        self._write_session_and_log(
            package, decision_titles, pattern_titles, dry_run, result
        )
        if not dry_run:
            self._write_log(package, result)
        return result

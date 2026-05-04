"""Archive cold notes: move to vault/011-archive/ and mark status=archived."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import frontmatter

from cma.config import CMAConfig
from cma.health.report import read_retrieval_log
from cma.storage.markdown_store import parse_vault


@dataclass
class ArchiveResult:
    moved: list[tuple[Path, Path]] = field(default_factory=list)  # (from, to)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (note_title, reason)
    dry_run: bool = False

    def summary(self) -> str:
        verb = "would archive" if self.dry_run else "archived"
        return f"{verb}={len(self.moved)} skipped={len(self.skipped)}"


def archive_note(vault_path: Path, note_path: Path) -> Path:
    """Move a single note file to vault/011-archive/ and set status=archived."""
    vault_path = Path(vault_path)
    note_path = Path(note_path)
    archive_dir = vault_path / "011-archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    target = archive_dir / note_path.name
    if target.exists() and target.resolve() != note_path.resolve():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = archive_dir / f"{note_path.stem}-archived-{stamp}.md"

    with open(note_path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    post["status"] = "archived"
    post["archived_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    target.write_text(frontmatter.dumps(post), encoding="utf-8")
    if note_path.resolve() != target.resolve():
        note_path.unlink()
    return target


def _build_last_seen_map(state_dir: Path) -> dict[str, datetime]:
    """Map note title -> last retrieval timestamp from the retrieval log."""
    last_seen: dict[str, datetime] = {}
    for ev in read_retrieval_log(state_dir):
        ts = ev.get("timestamp")
        if not ts:
            continue
        try:
            t = datetime.fromisoformat(ts)
        except ValueError:
            continue
        for nid in ev.get("node_ids", []):
            existing = last_seen.get(nid)
            if existing is None or t > existing:
                last_seen[nid] = t
    return last_seen


def archive_cold_notes(
    project_path: Path,
    *,
    older_than_days: int | None = None,
    note_type: str | None = None,
    only_status: str | None = None,
    dry_run: bool = False,
) -> ArchiveResult:
    """Archive notes matching the criteria.

    Args:
        older_than_days: archive only notes whose last retrieval (or, if never
            retrieved, whose `created` frontmatter) is older than this many days.
            Notes with no retrieval history AND no `created` field are skipped
            (we can't tell how old they are).
        note_type: only archive notes with this `type` frontmatter value.
        only_status: only archive notes with this `status` frontmatter value.
        dry_run: report what would be archived without touching the filesystem.

    Already-archived notes are always skipped.
    """
    project_path = Path(project_path).resolve()
    config = CMAConfig.from_project(project_path).resolve_paths(project_path)
    vault_path = Path(config.vault_path)
    state_dir = Path(config.index_path) / "state"

    last_seen = _build_last_seen_map(state_dir)
    cutoff: datetime | None = None
    if older_than_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    result = ArchiveResult(dry_run=dry_run)
    records = parse_vault(vault_path)

    for rec in records:
        label = rec.title

        if rec.status == "archived":
            result.skipped.append((label, "already archived"))
            continue
        if note_type is not None and rec.type != note_type:
            continue
        if only_status is not None and rec.status != only_status:
            continue

        if cutoff is not None:
            last = last_seen.get(rec.title) or last_seen.get(rec.record_id)
            if last is None and rec.created_at is not None:
                last = rec.created_at
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
            if last is None:
                result.skipped.append((label, "no age signal (never retrieved, no created date)"))
                continue
            if last >= cutoff:
                result.skipped.append((label, f"recent (last activity {last.date()})"))
                continue

        note_path = vault_path / rec.path
        if dry_run:
            archive_dir = vault_path / "011-archive"
            target = archive_dir / note_path.name
            result.moved.append((note_path, target))
        else:
            new_path = archive_note(vault_path, note_path)
            result.moved.append((note_path, new_path))

    return result

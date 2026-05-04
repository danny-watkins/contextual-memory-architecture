"""Parse an Obsidian-compatible markdown vault into MemoryRecord objects."""

import re
from datetime import datetime
from pathlib import Path

import frontmatter

from cma.schemas.memory_record import MEMORY_TYPES, MemoryRecord, VALID_STATUSES

WIKILINK_PATTERN = re.compile(r"\[\[([^\]\|#]+?)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")


def extract_wikilinks(text: str) -> list[str]:
    """Return wikilink targets from markdown text. Strips anchors and aliases.

    `[[Note]]`            -> "Note"
    `[[Note#Section]]`    -> "Note"
    `[[Note|alias]]`      -> "Note"
    """
    return [m.group(1).strip() for m in WIKILINK_PATTERN.finditer(text)]


def _coerce_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _coerce_tags(value) -> list[str]:
    if isinstance(value, list):
        return [str(t) for t in value]
    if isinstance(value, str):
        return [value]
    return []


def parse_note(vault_path: Path, file_path: Path) -> MemoryRecord:
    """Parse a single markdown file into a MemoryRecord."""
    vault_path = Path(vault_path)
    file_path = Path(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    fm = dict(post.metadata)
    body = post.content

    rel_path = file_path.relative_to(vault_path).as_posix()
    raw_type = fm.get("type", "note")
    note_type = raw_type if raw_type in MEMORY_TYPES else "note"
    title = fm.get("title") or file_path.stem
    status = fm.get("status", "active")
    if status not in VALID_STATUSES:
        status = "active"

    return MemoryRecord(
        record_id=file_path.stem,
        type=note_type,
        title=str(title),
        path=rel_path,
        created_at=_coerce_datetime(fm.get("created")),
        task_id=fm.get("task_id"),
        domain=fm.get("domain"),
        confidence=fm.get("confidence") if isinstance(fm.get("confidence"), (int, float)) else None,
        status=status,
        links=extract_wikilinks(body),
        tags=_coerce_tags(fm.get("tags")),
        human_verified=bool(fm.get("human_verified", False)),
        body=body,
        frontmatter=fm,
    )


def walk_vault(vault_path: Path) -> list[Path]:
    """Return every .md file under the vault, sorted."""
    vault_path = Path(vault_path)
    if not vault_path.exists():
        return []
    return sorted(p for p in vault_path.rglob("*.md") if p.is_file())


def parse_vault(vault_path: Path) -> list[MemoryRecord]:
    """Parse every markdown note in the vault."""
    vault_path = Path(vault_path)
    return [parse_note(vault_path, p) for p in walk_vault(vault_path)]

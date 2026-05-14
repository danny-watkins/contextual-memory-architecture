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
    """Parse a single markdown file into a MemoryRecord.

    Tolerant of malformed YAML frontmatter: if PyYAML raises on a file (for
    example, an unescaped Windows path in a quoted scalar), we fall back to
    treating the file as if it had no frontmatter at all -- the body still
    participates in retrieval, the note still becomes a graph node, and one
    bad file no longer takes the whole vault offline.
    """
    vault_path = Path(vault_path)
    file_path = Path(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        fm = dict(post.metadata)
        body = post.content
    except Exception:
        # Read the raw file, strip a leading frontmatter block heuristically, keep the body.
        try:
            raw = file_path.read_text(encoding="utf-8")
        except Exception:
            raw = ""
        fm = {}
        body = raw
        if raw.startswith("---\n"):
            # Drop the first --- ... --- block; everything after is the body.
            rest = raw[4:]
            end = rest.find("\n---\n")
            if end != -1:
                body = rest[end + 5:]

    rel_path = file_path.relative_to(vault_path).as_posix()
    raw_type = fm.get("type", "note")
    note_type = raw_type if raw_type in MEMORY_TYPES else "note"
    title = fm.get("title") or file_path.stem
    status = fm.get("status", "active")
    if status not in VALID_STATUSES:
        status = "active"

    tier = fm.get("tier")
    if tier not in ("memory", "substrate"):
        tier = "memory"

    return MemoryRecord(
        record_id=file_path.stem,
        type=note_type,
        tier=tier,
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
    """Parse every markdown note in the vault.

    Best-effort: any per-file failure that parse_note's own fallback also can't
    rescue (e.g. unreadable bytes) is swallowed -- one bad note must not take
    the whole vault offline. Skipped paths are accessible via the optional
    sidecar list returned alongside the records if a caller passes
    `return_skipped=True`; here we just drop them silently.
    """
    vault_path = Path(vault_path)
    out: list[MemoryRecord] = []
    for p in walk_vault(vault_path):
        try:
            out.append(parse_note(vault_path, p))
        except Exception:
            continue
    return out


def update_frontmatter(file_path: Path, updates: dict) -> None:
    """Merge `updates` into a note's YAML frontmatter and write back in place.

    Used by the Retriever to stamp `last_retrieved_at` and `retrieve_count` on
    notes that contributed to a Context Spec. The body is preserved exactly.
    """
    file_path = Path(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    for key, value in updates.items():
        post[key] = value
    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(frontmatter.dumps(post))
        f.write("\n")

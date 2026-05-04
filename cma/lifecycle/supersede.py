"""Mark a decision as superseded by a newer one.

Updates the old note's frontmatter (status=superseded, superseded_by=<new>,
superseded_at) and appends a wikilink to the new note in the body. Both notes
must already exist in the vault.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from cma.config import CMAConfig
from cma.storage.markdown_store import parse_vault


def supersede_decision(
    project_path: Path,
    old_title: str,
    new_title: str,
    dry_run: bool = False,
) -> Path | None:
    """Mark `old_title` as superseded by `new_title`. Returns the path of the
    updated old note, or None on dry_run.

    Raises ValueError if either note can't be located in the vault.
    """
    project_path = Path(project_path).resolve()
    config = CMAConfig.from_project(project_path).resolve_paths(project_path)
    vault_path = Path(config.vault_path)

    records = parse_vault(vault_path)
    old_rec = None
    new_rec = None
    for rec in records:
        if rec.title.lower() == old_title.lower() or rec.record_id.lower() == old_title.lower():
            old_rec = rec
        if rec.title.lower() == new_title.lower() or rec.record_id.lower() == new_title.lower():
            new_rec = rec

    if old_rec is None:
        raise ValueError(f"Note not found in vault: {old_title}")
    if new_rec is None:
        raise ValueError(f"Note not found in vault: {new_title}")
    if old_rec.record_id == new_rec.record_id:
        raise ValueError("A note cannot supersede itself")

    note_path = vault_path / old_rec.path

    with open(note_path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    post["status"] = "superseded"
    post["superseded_by"] = new_rec.title
    post["superseded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    body = post.content
    marker = f"**Superseded by [[{new_rec.title}]].**"
    if marker not in body:
        body = body.rstrip() + "\n\n" + marker + "\n"
    post.content = body

    if dry_run:
        return None

    note_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return note_path

"""Backfill `tier:` frontmatter on existing vault notes.

Vaults created before the two-tier ingestion change (2026-05-13) don't have
the `tier:` field. The Obsidian default graph view groups by `type:` first
but falls through to `tier:` for the substrate filter — without that field,
substrate stays visible and the graph looks like a hairball.

This module rewalks the vault, infers the tier from the existing `type:`
frontmatter (or defaults to memory for typeless notes), and writes the field
back. With `move_files=True`, substrate notes living under `020-sources/` are
relocated to the parallel `020-substrate/` tree so the folder convention
matches the frontmatter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

from cma.ingest import _classify_tier


@dataclass
class MigrateTierResult:
    backfilled: list[tuple[Path, str]] = field(default_factory=list)  # (path, tier)
    moved: list[tuple[Path, Path]] = field(default_factory=list)       # (from, to)
    already_tagged: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)      # (path, reason)
    dry_run: bool = False

    def summary(self) -> str:
        verb = "would backfill" if self.dry_run else "backfilled"
        move_verb = "would move" if self.dry_run else "moved"
        return (
            f"{verb}={len(self.backfilled)} {move_verb}={len(self.moved)} "
            f"already={len(self.already_tagged)} skipped={len(self.skipped)}"
        )


# Folders whose contents are CMA-managed lifecycle artifacts (already in their
# final resting place); migration leaves them alone.
_SKIP_FOLDERS = {"011-archive"}


def _is_in_sources_tree(note_path: Path, vault_path: Path) -> bool:
    try:
        rel = note_path.resolve().relative_to(vault_path.resolve())
    except ValueError:
        return False
    return rel.parts and rel.parts[0] == "020-sources"


def _substrate_target(note_path: Path, vault_path: Path) -> Path:
    """Mirror the note's location under 020-substrate/ instead of 020-sources/."""
    rel = note_path.resolve().relative_to(vault_path.resolve())
    return vault_path / "020-substrate" / Path(*rel.parts[1:])


def migrate_vault_tiers(
    vault_path: Path,
    *,
    move_files: bool = False,
    dry_run: bool = False,
) -> MigrateTierResult:
    """Walk `vault_path`, backfill `tier:` frontmatter, optionally move substrate."""
    vault_path = Path(vault_path).resolve()
    result = MigrateTierResult(dry_run=dry_run)

    if not vault_path.is_dir():
        result.skipped.append((vault_path, "vault path is not a directory"))
        return result

    for note_path in sorted(vault_path.rglob("*.md")):
        rel_parts = note_path.relative_to(vault_path).parts
        if rel_parts and rel_parts[0] in _SKIP_FOLDERS:
            continue

        try:
            with open(note_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
        except Exception as exc:
            result.skipped.append((note_path, f"unreadable: {exc}"))
            continue

        existing_tier = post.metadata.get("tier")
        if existing_tier:
            result.already_tagged.append(note_path)
            # If --move-files and the existing tier is substrate but the file
            # is under 020-sources/, still relocate it. This catches partial
            # migrations (someone edited frontmatter by hand but didn't move).
            if (
                move_files
                and existing_tier == "substrate"
                and _is_in_sources_tree(note_path, vault_path)
            ):
                target = _substrate_target(note_path, vault_path)
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    note_path.rename(target)
                result.moved.append((note_path, target))
            continue

        detected_type = post.metadata.get("type")
        tier = _classify_tier(detected_type) if detected_type else "memory"

        if not dry_run:
            post["tier"] = tier
            note_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        result.backfilled.append((note_path, tier))

        if move_files and tier == "substrate" and _is_in_sources_tree(note_path, vault_path):
            target = _substrate_target(note_path, vault_path)
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                note_path.rename(target)
            result.moved.append((note_path, target))

    return result

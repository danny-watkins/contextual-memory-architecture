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

from cma.ingest import MEMORY_TYPES, SUBSTRATE_TYPES, _classify_tier


def _effective_type(meta: dict) -> str | None:
    """Pick the most informative type signal from frontmatter.

    Some ingestion paths (and user conventions like Obsidian's `entity_type:`)
    leave the real semantic type in a field other than `type:`. Honor those so
    a company note with `entity_type: company` is recognized as memory, not
    substrate, regardless of what the ingester wrote into `type:`.
    """
    semantic = meta.get("entity_type")
    if isinstance(semantic, str) and semantic.strip():
        return semantic.strip().lower()
    declared = meta.get("type")
    if isinstance(declared, str):
        return declared.strip().lower() or None
    return None


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


def _tree_root(note_path: Path, vault_path: Path) -> str | None:
    try:
        rel = note_path.resolve().relative_to(vault_path.resolve())
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


def _is_in_sources_tree(note_path: Path, vault_path: Path) -> bool:
    return _tree_root(note_path, vault_path) == "020-sources"


def _is_in_substrate_tree(note_path: Path, vault_path: Path) -> bool:
    return _tree_root(note_path, vault_path) == "020-substrate"


def _substrate_target(note_path: Path, vault_path: Path) -> Path:
    """Mirror the note's location under 020-substrate/ instead of 020-sources/."""
    rel = note_path.resolve().relative_to(vault_path.resolve())
    return vault_path / "020-substrate" / Path(*rel.parts[1:])


def _sources_target(note_path: Path, vault_path: Path) -> Path:
    """Mirror the note's location under 020-sources/ instead of 020-substrate/."""
    rel = note_path.resolve().relative_to(vault_path.resolve())
    return vault_path / "020-sources" / Path(*rel.parts[1:])


def _correct_tier_for_meta(meta: dict) -> str:
    """The tier this note *should* have given everything we know about it."""
    effective = _effective_type(meta)
    return _classify_tier(effective) if effective else "memory"


def migrate_vault_tiers(
    vault_path: Path,
    *,
    move_files: bool = False,
    dry_run: bool = False,
) -> MigrateTierResult:
    """Walk `vault_path`, backfill or correct `tier:` frontmatter, optionally
    move files to match.

    Smart about pre-existing tier tags: if the declared `tier:` disagrees with
    what `entity_type:` (or `type:`) implies, the correct value wins. This is
    how a misclassified company note (ingested as `type: documentation`,
    tier defaulting to substrate, but really `entity_type: company`) gets
    pulled back into memory tier on a re-run.
    """
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

        correct_tier = _correct_tier_for_meta(post.metadata)
        existing_tier = post.metadata.get("tier")

        if existing_tier and existing_tier == correct_tier:
            result.already_tagged.append(note_path)
        else:
            # Backfill or correct.
            if not dry_run:
                post["tier"] = correct_tier
                note_path.write_text(frontmatter.dumps(post), encoding="utf-8")
            result.backfilled.append((note_path, correct_tier))

        if not move_files:
            continue

        # Move the file if its current folder disagrees with its tier.
        if correct_tier == "substrate" and _is_in_sources_tree(note_path, vault_path):
            target = _substrate_target(note_path, vault_path)
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                note_path.rename(target)
            result.moved.append((note_path, target))
        elif correct_tier == "memory" and _is_in_substrate_tree(note_path, vault_path):
            target = _sources_target(note_path, vault_path)
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                note_path.rename(target)
            result.moved.append((note_path, target))

    return result

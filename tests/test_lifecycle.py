from datetime import datetime, timedelta, timezone
from pathlib import Path

import frontmatter
import pytest

from cma.health import log_retrieval
from cma.lifecycle import archive_cold_notes, archive_note, supersede_decision


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "agent"
    project.mkdir()
    (project / "cma").mkdir(parents=True, exist_ok=True)
    (project / "cma" / "config.yaml").write_text(
        "vault_path: ./cma/vault\nindex_path: ./cma/cache\nembedding_provider: none\n",
        encoding="utf-8",
    )
    (project / "cma" / "vault" / "003-decisions").mkdir(parents=True)
    (project / "cma" / "vault" / "004-patterns").mkdir(parents=True)
    (project / "cma" / "vault" / "011-archive").mkdir(parents=True)
    return project


def _add_note(
    project: Path,
    folder: str,
    title: str,
    *,
    note_type: str = "note",
    status: str = "active",
    created: datetime | None = None,
) -> Path:
    fm = {"type": note_type, "title": title, "status": status}
    if created is not None:
        fm["created"] = created.isoformat()
    body = "\n".join(["---"] + [f"{k}: {v}" for k, v in fm.items()] + ["---", "", "Body."])
    path = project / "cma" / "vault" / folder / f"{title}.md"
    path.write_text(body, encoding="utf-8")
    return path


# ---------- archive_note ----------


def test_archive_note_moves_file_and_sets_status(tmp_path: Path):
    project = _project(tmp_path)
    src = _add_note(project, "003-decisions", "Old", note_type="decision", status="accepted")
    new_path = archive_note(project / "cma" / "vault", src)
    assert not src.exists()
    assert new_path.exists()
    assert new_path.parent.name == "011-archive"
    fm = frontmatter.load(open(new_path, "r", encoding="utf-8")).metadata
    assert fm["status"] == "archived"
    assert "archived_at" in fm


def test_archive_note_handles_filename_collision(tmp_path: Path):
    project = _project(tmp_path)
    a = _add_note(project, "003-decisions", "Twin")
    # Pre-create a different file at the archive target name.
    target = project / "cma" / "vault" / "011-archive" / "Twin.md"
    target.write_text("# pre-existing", encoding="utf-8")
    new_path = archive_note(project / "cma" / "vault", a)
    assert new_path != target
    assert new_path.exists()
    assert "archived" in new_path.name


# ---------- archive_cold_notes ----------


def test_archive_cold_notes_dry_run_changes_nothing(tmp_path: Path):
    project = _project(tmp_path)
    note = _add_note(project, "004-patterns", "Cold", note_type="pattern")
    result = archive_cold_notes(project, note_type="pattern", dry_run=True)
    assert len(result.moved) == 1
    assert note.exists()  # not actually moved


def test_archive_cold_notes_skips_already_archived(tmp_path: Path):
    project = _project(tmp_path)
    _add_note(project, "004-patterns", "Active One", note_type="pattern", status="active")
    _add_note(project, "011-archive", "Old One", note_type="pattern", status="archived")
    result = archive_cold_notes(project, note_type="pattern")
    moved_titles = {src.stem for src, _ in result.moved}
    assert "Active One" in moved_titles
    assert "Old One" not in moved_titles


def test_archive_cold_notes_filters_by_type(tmp_path: Path):
    project = _project(tmp_path)
    _add_note(project, "003-decisions", "DecOne", note_type="decision")
    _add_note(project, "004-patterns", "PatOne", note_type="pattern")
    result = archive_cold_notes(project, note_type="pattern")
    moved_titles = {src.stem for src, _ in result.moved}
    assert moved_titles == {"PatOne"}


def test_archive_cold_notes_filters_by_status(tmp_path: Path):
    project = _project(tmp_path)
    _add_note(project, "003-decisions", "Accepted", note_type="decision", status="accepted")
    _add_note(project, "003-decisions", "Drafty", note_type="decision", status="draft")
    result = archive_cold_notes(project, only_status="draft")
    moved_titles = {src.stem for src, _ in result.moved}
    assert moved_titles == {"Drafty"}


def test_archive_cold_notes_uses_retrieval_log_age(tmp_path: Path):
    """A note retrieved recently should be skipped; a stale one should be archived."""
    project = _project(tmp_path)
    _add_note(project, "004-patterns", "Hot", note_type="pattern")
    _add_note(project, "004-patterns", "Stale", note_type="pattern")
    # Log a recent retrieval for "Hot" only
    log_retrieval(
        project,
        spec_id="s",
        task_id="t",
        query="q",
        fragment_titles=["Hot"],
        token_estimate=10,
        fragment_count=1,
    )
    # Use a very small cutoff (0 days = anything before now is stale, but Hot was just logged)
    # Set older_than_days=1: anything not retrieved in past 24h is stale.
    # "Stale" has no log entry and no created date -> skipped (no age signal).
    # But we want it archived. So give it a created date in the past.
    stale_path = project / "cma" / "vault" / "004-patterns" / "Stale.md"
    stale_path.write_text(
        "---\ntype: pattern\ntitle: Stale\nstatus: active\ncreated: 2020-01-01T00:00:00\n---\n\nBody.\n",
        encoding="utf-8",
    )
    result = archive_cold_notes(project, older_than_days=1, dry_run=True)
    titles = {src.stem for src, _ in result.moved}
    assert "Stale" in titles
    assert "Hot" not in titles


def test_archive_cold_notes_skips_notes_without_age_signal(tmp_path: Path):
    """No retrieval history AND no created date -> skip (we can't tell its age)."""
    project = _project(tmp_path)
    _add_note(project, "004-patterns", "Mystery", note_type="pattern")
    result = archive_cold_notes(project, older_than_days=30)
    skipped_titles = {title for title, _ in result.skipped}
    assert "Mystery" in skipped_titles


# ---------- supersede ----------


def test_supersede_updates_old_note(tmp_path: Path):
    project = _project(tmp_path)
    old_path = _add_note(
        project, "003-decisions", "Old Decision", note_type="decision", status="accepted"
    )
    _add_note(project, "003-decisions", "New Decision", note_type="decision", status="accepted")
    updated = supersede_decision(project, "Old Decision", "New Decision")
    assert updated == old_path
    fm = frontmatter.load(open(old_path, "r", encoding="utf-8"))
    assert fm["status"] == "superseded"
    assert fm["superseded_by"] == "New Decision"
    assert "[[New Decision]]" in fm.content


def test_supersede_dry_run_makes_no_changes(tmp_path: Path):
    project = _project(tmp_path)
    old = _add_note(project, "003-decisions", "Old Decision", note_type="decision")
    _add_note(project, "003-decisions", "New Decision", note_type="decision")
    result = supersede_decision(project, "Old Decision", "New Decision", dry_run=True)
    assert result is None
    fm = frontmatter.load(open(old, "r", encoding="utf-8"))
    assert fm["status"] != "superseded"


def test_supersede_raises_on_missing_note(tmp_path: Path):
    project = _project(tmp_path)
    _add_note(project, "003-decisions", "Exists")
    with pytest.raises(ValueError):
        supersede_decision(project, "Does Not Exist", "Exists")
    with pytest.raises(ValueError):
        supersede_decision(project, "Exists", "Also Does Not Exist")


def test_supersede_self_raises(tmp_path: Path):
    project = _project(tmp_path)
    _add_note(project, "003-decisions", "Self")
    with pytest.raises(ValueError):
        supersede_decision(project, "Self", "Self")

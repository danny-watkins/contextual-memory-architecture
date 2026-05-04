from pathlib import Path

from cma.storage.markdown_store import extract_wikilinks, parse_note, parse_vault, walk_vault


def test_extract_wikilinks_basic():
    text = "See [[Capital Call Processing]] and [[Queue Retry Pattern|the retry pattern]]."
    assert extract_wikilinks(text) == ["Capital Call Processing", "Queue Retry Pattern"]


def test_extract_wikilinks_with_header():
    text = "Refer to [[Some Note#Section]]."
    assert extract_wikilinks(text) == ["Some Note"]


def test_extract_wikilinks_with_alias_and_header():
    text = "Mix: [[A Note#Heading|alias]]."
    assert extract_wikilinks(text) == ["A Note"]


def test_extract_wikilinks_empty():
    assert extract_wikilinks("just plain text without links") == []


def test_extract_wikilinks_multiple_per_line():
    text = "[[A]] and [[B]] together with [[C]]."
    assert extract_wikilinks(text) == ["A", "B", "C"]


def test_parse_note_with_frontmatter(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "Decision.md"
    note.write_text(
        """---
type: decision
title: Test Decision
status: accepted
confidence: 0.86
tags: [backend, performance]
domain: engineering
---

# Test Decision

We chose to do X. Links to [[Other Note]].
""",
        encoding="utf-8",
    )
    rec = parse_note(vault, note)
    assert rec.type == "decision"
    assert rec.title == "Test Decision"
    assert rec.status == "accepted"
    assert rec.confidence == 0.86
    assert "backend" in rec.tags
    assert rec.domain == "engineering"
    assert rec.links == ["Other Note"]
    assert rec.path == "Decision.md"


def test_parse_note_no_frontmatter_uses_filename(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "Plain Note.md"
    note.write_text("# Plain Note\n\nNo metadata here.", encoding="utf-8")
    rec = parse_note(vault, note)
    assert rec.title == "Plain Note"
    assert rec.type == "note"
    assert rec.status == "active"
    assert rec.tags == []


def test_parse_note_unknown_type_falls_back_to_note(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "X.md"
    note.write_text(
        """---
type: not_a_real_type
---
body
""",
        encoding="utf-8",
    )
    rec = parse_note(vault, note)
    assert rec.type == "note"


def test_walk_vault_returns_empty_for_missing(tmp_path: Path):
    assert walk_vault(tmp_path / "does-not-exist") == []


def test_parse_vault_walks_subdirs(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "001-projects").mkdir(parents=True)
    (vault / "001-projects" / "Project A.md").write_text(
        "# A\nLinks to [[B]].", encoding="utf-8"
    )
    (vault / "002-sessions").mkdir()
    (vault / "002-sessions" / "B.md").write_text("# B\nNo links.", encoding="utf-8")
    records = parse_vault(vault)
    assert len(records) == 2
    titles = {r.title for r in records}
    assert titles == {"Project A", "B"}

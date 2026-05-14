"""Tests for `cma migrate-tier` — the existing-vault migration that backfills
`tier:` frontmatter and optionally relocates substrate notes."""

from pathlib import Path

import frontmatter
from typer.testing import CliRunner

from cma.cli import app
from cma.lifecycle import migrate_vault_tiers

runner = CliRunner()


def _seed_vault(project: Path) -> Path:
    """Initialize a project and drop a pre-two-tier vault layout into it.
    Returns the vault path."""
    runner.invoke(app, ["init", str(project)])
    vault = project / "cma" / "vault"
    # Memory-tier note in the old location (decision under 020-sources).
    (vault / "020-sources" / "app").mkdir(parents=True)
    (vault / "020-sources" / "app" / "use-postgres.md").write_text(
        "---\ntype: decision\ntitle: Use Postgres\nstatus: accepted\n---\n\nACID.\n",
        encoding="utf-8",
    )
    # Substrate-tier note in the old location (code under 020-sources).
    (vault / "020-sources" / "app" / "main-py.md").write_text(
        "---\ntype: code\ntitle: main.py\n---\n\n```python\ndef hello(): pass\n```\n",
        encoding="utf-8",
    )
    # A note that already has tier: set (should be left alone).
    (vault / "003-decisions" / "Already Tagged.md").write_text(
        "---\ntype: decision\ntier: memory\ntitle: Already Tagged\n---\n\nNo change.\n",
        encoding="utf-8",
    )
    # A note without any type frontmatter (should default to memory).
    (vault / "000-inbox" / "Scratch.md").write_text(
        "---\ntitle: Scratch\n---\n\nA random scratch note.\n",
        encoding="utf-8",
    )
    return vault


def _read_meta(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return dict(frontmatter.load(f).metadata)


def test_migrate_backfills_tier_on_untagged_notes(tmp_path: Path):
    project = tmp_path / "agent"
    vault = _seed_vault(project)

    result = migrate_vault_tiers(vault)

    # Decision (memory-tier) and code (substrate-tier) both backfilled.
    # 5 untagged total: 3 we seeded (decision, code, scratch) + 2 from cma init
    # (Welcome.md, Quickstart.md in 000-inbox).
    assert len(result.backfilled) == 5, result.summary()
    # Both notes now declare their tier.
    decision_meta = _read_meta(vault / "020-sources" / "app" / "use-postgres.md")
    code_meta = _read_meta(vault / "020-sources" / "app" / "main-py.md")
    scratch_meta = _read_meta(vault / "000-inbox" / "Scratch.md")
    assert decision_meta["tier"] == "memory"
    assert code_meta["tier"] == "substrate"
    assert scratch_meta["tier"] == "memory"  # typeless defaults to memory


def test_migrate_leaves_already_tagged_notes_alone(tmp_path: Path):
    project = tmp_path / "agent"
    vault = _seed_vault(project)

    result = migrate_vault_tiers(vault)

    assert len(result.already_tagged) == 1
    tagged_meta = _read_meta(vault / "003-decisions" / "Already Tagged.md")
    assert tagged_meta["tier"] == "memory"


def test_migrate_dry_run_writes_nothing(tmp_path: Path):
    project = tmp_path / "agent"
    vault = _seed_vault(project)

    result = migrate_vault_tiers(vault, dry_run=True)
    assert result.dry_run
    assert len(result.backfilled) == 5

    # File contents must be unchanged.
    decision_meta = _read_meta(vault / "020-sources" / "app" / "use-postgres.md")
    assert "tier" not in decision_meta
    code_meta = _read_meta(vault / "020-sources" / "app" / "main-py.md")
    assert "tier" not in code_meta


def test_migrate_move_files_relocates_substrate(tmp_path: Path):
    project = tmp_path / "agent"
    vault = _seed_vault(project)

    result = migrate_vault_tiers(vault, move_files=True)

    # Substrate note moved out of 020-sources/.
    assert not (vault / "020-sources" / "app" / "main-py.md").exists()
    assert (vault / "020-substrate" / "app" / "main-py.md").exists()
    # Memory-tier decision stays where it was.
    assert (vault / "020-sources" / "app" / "use-postgres.md").exists()
    assert len(result.moved) == 1


def test_migrate_tier_cli_outputs_summary(tmp_path: Path):
    project = tmp_path / "agent"
    _seed_vault(project)

    result = runner.invoke(app, ["migrate-tier", "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert "Backfilled" in result.output
    assert "Next:" in result.output  # the post-run hint to reindex


def test_migrate_honors_entity_type_over_type(tmp_path: Path):
    """A note ingested as `type: documentation` but with `entity_type: company`
    should land in memory tier, not substrate. This is the Obsidian-KB
    convention many users follow."""
    project = tmp_path / "agent"
    runner.invoke(app, ["init", str(project)])
    vault = project / "cma" / "vault"
    (vault / "020-sources" / "companies").mkdir(parents=True)
    (vault / "020-sources" / "companies" / "anthropic.md").write_text(
        "---\n"
        "type: documentation\n"
        "entity_type: company\n"
        "title: Anthropic\n"
        "---\n\n"
        "A company we applied to.\n",
        encoding="utf-8",
    )

    result = migrate_vault_tiers(vault, move_files=True)

    # entity_type wins — this is memory, not substrate.
    meta = _read_meta(vault / "020-sources" / "companies" / "anthropic.md")
    assert meta["tier"] == "memory"
    # And the file stays in 020-sources/.
    assert not (vault / "020-substrate" / "companies" / "anthropic.md").exists()


def test_migrate_corrects_misclassified_substrate_back_to_memory(tmp_path: Path):
    """A note previously migrated to substrate (because type was 'documentation')
    that has entity_type set should be pulled back to memory and physically
    moved from 020-substrate/ to 020-sources/ on a corrective re-run."""
    project = tmp_path / "agent"
    runner.invoke(app, ["init", str(project)])
    vault = project / "cma" / "vault"
    (vault / "020-substrate" / "companies").mkdir(parents=True)
    (vault / "020-substrate" / "companies" / "anthropic.md").write_text(
        "---\n"
        "type: documentation\n"
        "entity_type: company\n"
        "tier: substrate\n"
        "title: Anthropic\n"
        "---\n\n"
        "A company we applied to.\n",
        encoding="utf-8",
    )

    result = migrate_vault_tiers(vault, move_files=True)

    assert not (vault / "020-substrate" / "companies" / "anthropic.md").exists()
    assert (vault / "020-sources" / "companies" / "anthropic.md").exists()
    meta = _read_meta(vault / "020-sources" / "companies" / "anthropic.md")
    assert meta["tier"] == "memory"


def test_migrate_tier_cli_dry_run(tmp_path: Path):
    project = tmp_path / "agent"
    vault = _seed_vault(project)

    result = runner.invoke(
        app, ["migrate-tier", "--project", str(project), "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "DRY RUN" in result.output
    # File unchanged.
    code_meta = _read_meta(vault / "020-sources" / "app" / "main-py.md")
    assert "tier" not in code_meta

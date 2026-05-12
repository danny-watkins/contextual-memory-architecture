import json
from pathlib import Path

import pytest

from cma.health import THRESHOLDS, health_report, log_retrieval, read_retrieval_log


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
    (project / "cma" / "cache" / "state").mkdir(parents=True)
    (project / "cma" / "vault" / "003-decisions" / "Decision A.md").write_text(
        "---\ntype: decision\ntitle: Decision A\nstatus: accepted\n---\n\nLinks to [[Pattern X]].\n",
        encoding="utf-8",
    )
    (project / "cma" / "vault" / "004-patterns" / "Pattern X.md").write_text(
        "---\ntype: pattern\ntitle: Pattern X\nstatus: active\n---\n\nA pattern body.\n",
        encoding="utf-8",
    )
    return project


def test_health_report_vault_breakdown(tmp_path: Path):
    project = _project(tmp_path)
    report = health_report(project)
    assert report["vault"]["total_notes"] == 2
    assert "003-decisions" in report["vault"]["by_folder"]
    assert "004-patterns" in report["vault"]["by_folder"]
    assert report["vault"]["by_folder"]["003-decisions"]["notes"] == 1


def test_health_report_graph_metrics(tmp_path: Path):
    project = _project(tmp_path)
    report = health_report(project)
    g = report["graph"]
    assert g["total_nodes"] == 2
    assert g["total_edges"] == 1
    assert g["broken_links"] == 0
    assert g["orphans"] == 0


def test_health_report_no_retrieval_log(tmp_path: Path):
    project = _project(tmp_path)
    report = health_report(project)
    r = report["retrieval"]
    assert r["total_events"] == 0
    assert r["never_retrieved"] == 2  # both notes never retrieved


def test_log_retrieval_appends_jsonl(tmp_path: Path):
    project = _project(tmp_path)
    log_retrieval(
        project,
        spec_id="spec-1",
        task_id="t1",
        query="test query",
        fragment_titles=["Decision A"],
        token_estimate=100,
        fragment_count=2,
    )
    log_retrieval(
        project,
        spec_id="spec-2",
        task_id="t2",
        query="other",
        fragment_titles=["Decision A", "Pattern X"],
        token_estimate=200,
        fragment_count=4,
    )
    events = read_retrieval_log(project / "cma" / "cache" / "state")
    assert len(events) == 2
    assert events[0]["query"] == "test query"
    assert events[1]["fragment_count"] == 4


def test_health_report_with_retrieval_log(tmp_path: Path):
    project = _project(tmp_path)
    log_retrieval(
        project,
        spec_id="s",
        task_id="t",
        query="q",
        fragment_titles=["Decision A"],
        token_estimate=50,
        fragment_count=1,
    )
    report = health_report(project)
    r = report["retrieval"]
    assert r["total_events"] == 1
    assert r["never_retrieved"] == 1  # only Pattern X is never retrieved
    assert ("Decision A", 1) in r["most_retrieved"]


def test_health_warnings_for_broken_links(tmp_path: Path):
    project = _project(tmp_path)
    # Add a note with a broken link to push broken_link_rate above threshold.
    (project / "cma" / "vault" / "Bad.md").write_text(
        "---\ntype: note\n---\n\nLinks to [[Nonexistent One]] and [[Nonexistent Two]].\n",
        encoding="utf-8",
    )
    report = health_report(project)
    # 2 broken links / 3 total edges = 67% > 5% threshold
    assert any("Broken link rate" in w for w in report["warnings"])


def test_health_no_warnings_on_clean_vault(tmp_path: Path):
    project = _project(tmp_path)
    report = health_report(project)
    assert report["warnings"] == []


def test_health_thresholds_are_documented():
    """The thresholds should be discoverable as a dict."""
    assert "vault_notes" in THRESHOLDS
    assert "embeddings_bytes" in THRESHOLDS
    assert "orphan_rate" in THRESHOLDS


def test_health_index_byte_counts(tmp_path: Path):
    project = _project(tmp_path)
    # Drop a file in each index folder so we can verify they get counted.
    bm25_dir = project / "cma" / "cache" / "bm25"
    bm25_dir.mkdir(parents=True)
    (bm25_dir / "index.pkl").write_bytes(b"x" * 1000)
    emb_dir = project / "cma" / "cache" / "embeddings"
    emb_dir.mkdir(parents=True)
    (emb_dir / "embeddings.npy").write_bytes(b"y" * 2000)
    (emb_dir / "meta.json").write_text(
        json.dumps({"embedder": "test", "dim": 384, "n_docs": 2}),
        encoding="utf-8",
    )
    report = health_report(project)
    assert report["indexes"]["bm25"]["bytes"] >= 1000
    assert report["indexes"]["embeddings"]["bytes"] >= 2000
    assert report["indexes"]["embeddings"]["dim"] == 384
    assert report["indexes"]["embeddings"]["n_docs"] == 2


def test_retriever_logs_retrieval_calls(tmp_path: Path):
    """Integration test: Retriever.from_project should write to retrieval_log.jsonl."""
    from cma.retriever import Retriever
    project = _project(tmp_path)
    retriever = Retriever.from_project(project)
    retriever.retrieve("decision A")
    log_path = project / "cma" / "cache" / "state" / "retrieval_log.jsonl"
    assert log_path.exists()
    events = read_retrieval_log(project / "cma" / "cache" / "state")
    assert len(events) >= 1
    assert events[0]["query"] == "decision A"

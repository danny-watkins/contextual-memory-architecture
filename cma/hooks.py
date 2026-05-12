"""Claude Code hook entry points for automatic CMA firing.

Two hooks, registered in <project>/.claude/settings.json by `cma add`:

- UserPromptSubmit -> `cma hook user-prompt`: captures the user's prompt to the
  inbox (`000-inbox/prompts/<date>/<hash>.md`), runs a fast BM25-only retrieval,
  and prints the rendered Context Spec to stdout so Claude Code injects it into
  the agent's pre-turn context.

- Stop -> `cma hook stop`: appends a lightweight session summary to
  `002-sessions/<session-id>.md`. Does not try to extract decisions or patterns
  automatically -- that remains the cma-recorder sub-agent's job, invoked
  deliberately when the agent wants to commit a CompletionPackage.

The hook scripts are intentionally cheap (no embedding-model cold start, no LLM
call) so they fire on every prompt without adding noticeable latency. The MCP
server is still available for deep retrieves on demand.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cma.activity import log_activity


# ---------- helpers ----------


def _hook_input() -> dict[str, Any]:
    """Read the hook payload from stdin. Returns {} on parse failure (hooks must not crash)."""
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _debug_log(event: str, **fields: Any) -> None:
    """Append a debug line to cma/memory_log/hook_debug.log next to the project.

    Disabled by default; set CMA_HOOK_DEBUG=1 to enable. Useful when a hook is
    misbehaving inside the host runtime where normal stdout/stderr are captured
    silently. The file lives next to activity.jsonl so it's easy to inspect
    alongside real events.
    """
    if not os.environ.get("CMA_HOOK_DEBUG"):
        return
    try:
        cwd = Path.cwd()
        for candidate in [cwd, *cwd.parents]:
            if (candidate / "cma" / "config.yaml").exists():
                log = candidate / "cma" / "memory_log" / "hook_debug.log"
                log.parent.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(timezone.utc).isoformat()
                line = f"{stamp} [{event}] " + " ".join(
                    f"{k}={json.dumps(v) if not isinstance(v, str) else v!r}"
                    for k, v in fields.items()
                )
                with open(log, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                return
    except Exception:
        pass


def _resolve_project(payload: dict[str, Any]) -> Path | None:
    """Locate the CMA project root from the hook payload's cwd."""
    cwd = payload.get("cwd") or Path.cwd()
    path = Path(cwd).resolve()
    # Walk up to find a cma/config.yaml -- the project root is its parent.
    for candidate in [path, *path.parents]:
        if (candidate / "cma" / "config.yaml").exists():
            return candidate
    return None


def _short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_hhmm() -> str:
    return datetime.now(timezone.utc).strftime("%H-%M-%S")


# ---------- UserPromptSubmit ----------


def _capture_prompt_to_inbox(project_path: Path, prompt: str, session_id: str | None) -> Path:
    """Write the prompt to cma/vault/000-inbox/prompts/<date>/<time>-<hash>.md. Return the path."""
    vault = project_path / "cma" / "vault"
    inbox = vault / "000-inbox" / "prompts" / _today()
    inbox.mkdir(parents=True, exist_ok=True)
    h = _short_hash(prompt)
    filename = f"{_now_hhmm()}-{h}.md"
    path = inbox / filename

    # Don't double-write the same prompt within the same hour-minute.
    if path.exists():
        return path

    title = prompt.strip().splitlines()[0][:80] if prompt.strip() else "(empty prompt)"
    body = (
        f"---\n"
        f"type: prompt\n"
        f"title: {json.dumps(title)}\n"
        f"status: noise\n"
        f"session_id: {session_id or 'unknown'}\n"
        f"captured_at: {datetime.now(timezone.utc).isoformat()}\n"
        f"---\n\n"
        f"# Prompt\n\n"
        f"```\n{prompt}\n```\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def _quick_retrieve(
    project_path: Path, prompt: str
) -> tuple[str | None, str | None, list[dict] | None]:
    """Run the FULL Retriever pipeline (BM25-only seeds, no embedding cold start).

    Returns (rendered_markdown, spec_id, per_source_artifacts). Any element may
    be None on failure.

    This is the Retriever from whitepaper §4 running end-to-end:
      1. Seed selection (BM25-only -- skip embedding model to keep the hook fast)
      2. Graph traversal from seeds, beam-pruned per config
      3. Fragment extraction (relevant chunks, not whole notes)
      4. Context Spec assembled and persisted to vault/008-context-specs/
      5. Spec rendered as markdown for the agent to read pre-turn

    The persisted spec note feeds the GraphRAG flywheel: future retrieves can
    find this spec as a relevant source, so memory compounds across turns.
    """
    try:
        from cma.retriever import Retriever, per_source_token_artifacts, render_markdown
        from cma.storage.markdown_store import parse_vault  # noqa: F401
    except Exception as e:
        _debug_log("quick_retrieve_import_failed", error=repr(e))
        return None, None, None

    try:
        # embedder="auto" runs the hybrid (BM25 + embeddings) seed selection
        # specified by the whitepaper §4.1. Per-hook cost: ~2-3s to load the
        # sentence-transformers model into the new process. Falls back to
        # BM25-only if the embedder dependency isn't installed (EmbedderUnavailable).
        retriever = Retriever.from_project(project_path, embedder="auto")
    except Exception as e:
        _debug_log("quick_retrieve_from_project_failed", error=repr(e))
        return None, None, None

    _debug_log("quick_retrieve_loaded", n_records=len(retriever.records))
    if not retriever.records:
        _debug_log("quick_retrieve_no_records_after_load")
        return None, None, None

    # Filter the seed pool BEFORE the pipeline runs:
    #   - Inbox prompts (status=noise) -> circular self-matches if kept.
    #   - Prior context_spec notes -> they contain query-keyword-heavy metadata
    #     ("## Sources", "From [[X]] / path") that dominates BM25 over the
    #     actual primary source content. Excluding them at the hook layer means
    #     the agent gets clean source fragments by default; if the agent wants
    #     the full GraphRAG flywheel (specs feeding specs) it calls
    #     mcp__cma__retrieve explicitly, which uses the unfiltered pool.
    retriever.records = [
        r for r in retriever.records
        if "000-inbox/prompts" not in r.path.replace("\\", "/")
        and r.frontmatter.get("status") != "noise"
        and r.type != "context_spec"
    ]
    retriever.records_by_id = {r.record_id: r for r in retriever.records}
    _debug_log("quick_retrieve_after_filter", n_records=len(retriever.records))
    if not retriever.records:
        _debug_log("quick_retrieve_no_records_after_filter")
        return None, None, None
    # Rebuild BM25 over the filtered set so the excluded record types don't
    # leak through the lexical side of the hybrid score.
    try:
        from cma.retriever.lexical import BM25Index
        retriever.bm25 = BM25Index(retriever.records)
    except Exception as e:
        _debug_log("quick_retrieve_bm25_rebuild_failed", error=repr(e))
    # Also rebuild the embedding index over the filtered set if the embedder loaded.
    if retriever.embedder is not None:
        try:
            from cma.retriever.embeddings import EmbeddingIndex
            retriever.embedding_index = EmbeddingIndex.build(retriever.records, retriever.embedder)
        except Exception as e:
            _debug_log("quick_retrieve_embedding_rebuild_failed", error=repr(e))

    try:
        spec = retriever.retrieve(prompt)
        _debug_log("quick_retrieve_spec_built", spec_id=getattr(spec, "spec_id", None), n_fragments=len(spec.fragments or []))
    except Exception as e:
        _debug_log("quick_retrieve_retrieve_failed", error=repr(e))
        return None, None, None

    if not spec.fragments:
        # No fragments above threshold means nothing relevant in the vault. Return a
        # tiny breadcrumb so the agent knows a retrieve was attempted, but with no hits.
        return (
            f"## CMA Context (auto-loaded)\n_query: {prompt[:200]}_\n\n"
            f"No notes in your vault scored above the relevance threshold. "
            f"This is your first interaction on this topic; nothing prior to draw from.\n",
            spec.spec_id,
            [],
        )

    rendered = render_markdown(spec)
    artifacts = per_source_token_artifacts(
        spec, retriever.records_by_id, vault_path=retriever.vault_path
    )
    return rendered, spec.spec_id, artifacts


def user_prompt_hook() -> int:
    """Entry point for the UserPromptSubmit hook. Reads stdin, writes stdout.

    Returns 0 on success (Claude Code reads stdout as additional context).
    Returns non-zero only on truly catastrophic failure; logging-style errors
    are silently swallowed.
    """
    _debug_log("user_prompt_hook_entered")
    payload = _hook_input()
    prompt = payload.get("prompt", "")
    session_id = payload.get("session_id")
    project = _resolve_project(payload)
    _debug_log(
        "user_prompt_hook_resolved",
        prompt_len=len(prompt),
        project=str(project) if project else None,
        session_id=session_id,
    )
    if project is None or not prompt:
        _debug_log("user_prompt_hook_early_exit", reason="no_project_or_prompt")
        return 0

    try:
        _capture_prompt_to_inbox(project, prompt, session_id)
    except Exception:
        pass

    # Run the full Retriever pipeline BEFORE logging, so we can attach the
    # resulting spec_id and per-source token info as artifacts on the event.
    context, spec_id, source_artifacts = _quick_retrieve(project, prompt)

    artifacts: list[dict] = []
    if spec_id:
        artifacts.append({
            "title": spec_id,
            "path": f"008-context-specs/{spec_id}.md",
            "kind": "spec",
        })
    if source_artifacts:
        artifacts.extend(source_artifacts)

    total_tokens_pulled = sum(a.get("tokens_extracted", 0) for a in source_artifacts or [])

    try:
        log_activity(
            project, "prompt",
            summary=prompt[:120],
            details={
                "len": len(prompt),
                "spec_id": spec_id,
                "n_sources": len(source_artifacts or []),
                "total_tokens_extracted": total_tokens_pulled,
            },
            artifacts=artifacts or None,
            session_id=session_id,  # group under the Claude Code session, not the hook PID
        )
    except Exception:
        pass

    if context:
        sys.stdout.write(context + "\n")
    return 0


# ---------- Stop ----------


def _append_session_summary(project_path: Path, session_id: str, transcript_path: str | None) -> Path:
    """Append a session summary to cma/vault/002-sessions/<session-id>.md."""
    vault = project_path / "cma" / "vault"
    sessions = vault / "002-sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    safe_sid = session_id or "unknown-session"
    safe_sid = "".join(c if c.isalnum() or c in "-_" else "-" for c in safe_sid)[:80]
    path = sessions / f"{safe_sid}.md"

    timestamp = datetime.now(timezone.utc).isoformat()
    if not path.exists():
        header = (
            f"---\n"
            f"type: session\n"
            f"title: {safe_sid}\n"
            f"status: active\n"
            f"created: {timestamp}\n"
            f"transcript_path: {json.dumps(transcript_path or '')}\n"
            f"---\n\n"
            f"# Session {safe_sid}\n\n"
            f"Auto-captured by the Stop hook. Use cma-recorder to formalize "
            f"decisions/patterns from this session.\n\n"
            f"## Events\n\n"
        )
        path.write_text(header, encoding="utf-8")

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"- {timestamp}: Stop event\n")
    return path


def stop_hook() -> int:
    """Entry point for the Stop hook. Captures session metadata, no LLM call."""
    payload = _hook_input()
    session_id = payload.get("session_id", "unknown")
    transcript_path = payload.get("transcript_path")
    project = _resolve_project(payload)
    if project is None:
        return 0

    try:
        _append_session_summary(project, session_id, transcript_path)
    except Exception:
        pass

    try:
        log_activity(
            project, "stop",
            summary=f"session {session_id[:12]} ended",
            details={"transcript_path": transcript_path},
            session_id=session_id,  # group under the Claude Code session
        )
    except Exception:
        pass
    return 0

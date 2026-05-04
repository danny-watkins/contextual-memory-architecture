"""Generate the CMA technical whitepaper PDF.

Run from repo root:
    python docs/build_whitepaper.py

Outputs:
    docs/CMA_Whitepaper_v0.4.pdf

The doc is regenerated from this script every release. To update content,
edit the SECTIONS list below and re-run.
"""

from __future__ import annotations

from pathlib import Path
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).parent / "CMA_Whitepaper_v0.4.pdf"
VERSION = "0.4.0"
TITLE = "Contextual Memory Architecture (CMA)"
SUBTITLE = "Technical Whitepaper & Implementation Reference"
TODAY = date.today().isoformat()

# ----- styles -----
styles = getSampleStyleSheet()

H_TITLE = ParagraphStyle(
    "HTitle", parent=styles["Title"], fontSize=28, leading=34, spaceAfter=12,
    textColor=colors.HexColor("#1a1a2e"),
)
H_SUB = ParagraphStyle(
    "HSub", parent=styles["Normal"], fontSize=14, leading=18, spaceAfter=24,
    textColor=colors.HexColor("#4a4e69"), fontName="Helvetica-Oblique",
)
H1 = ParagraphStyle(
    "H1", parent=styles["Heading1"], fontSize=18, leading=22, spaceBefore=18,
    spaceAfter=10, textColor=colors.HexColor("#0f3460"),
)
H2 = ParagraphStyle(
    "H2", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=14,
    spaceAfter=6, textColor=colors.HexColor("#0f3460"),
)
H3 = ParagraphStyle(
    "H3", parent=styles["Heading3"], fontSize=12, leading=16, spaceBefore=10,
    spaceAfter=4, textColor=colors.HexColor("#16213e"),
)
BODY = ParagraphStyle(
    "Body", parent=styles["Normal"], fontSize=10.5, leading=15,
    spaceAfter=8, alignment=TA_LEFT,
)
BULLET = ParagraphStyle(
    "Bullet", parent=BODY, leftIndent=18, bulletIndent=6, spaceAfter=4,
)
CODE = ParagraphStyle(
    "Code", parent=styles["Code"], fontSize=8.5, leading=11,
    backColor=colors.HexColor("#f4f4f4"), borderPadding=6,
    leftIndent=4, rightIndent=4, spaceAfter=10, spaceBefore=4,
    textColor=colors.HexColor("#202020"),
)
NOTE = ParagraphStyle(
    "Note", parent=BODY, leftIndent=12, rightIndent=12,
    backColor=colors.HexColor("#fffaf0"), borderPadding=8,
    spaceAfter=10, fontName="Helvetica-Oblique",
)


def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(inch * 0.75, inch * 0.5, f"CMA Whitepaper v{VERSION}")
    canvas.drawRightString(LETTER[0] - inch * 0.75, inch * 0.5, f"page {doc.page}")
    canvas.restoreState()


def _on_first_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(LETTER[0] / 2, inch * 0.5, f"CMA v{VERSION}")
    canvas.restoreState()


def code(text: str) -> Preformatted:
    return Preformatted(text.strip("\n"), CODE)


def para(text: str, style=BODY) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: list[str]) -> list:
    return [Paragraph(f"&bull;&nbsp; {t}", BULLET) for t in items]


def section_break() -> PageBreak:
    return PageBreak()


def make_table(headers: list[str], rows: list[list[str]]) -> Table:
    data = [headers] + rows
    t = Table(data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f8fc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f8")]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


# ----- content builder -----


def build_story() -> list:
    s: list = []

    # ---- title page ----
    s.append(Spacer(1, 1.5 * inch))
    s.append(Paragraph(TITLE, H_TITLE))
    s.append(Paragraph(SUBTITLE, H_SUB))
    s.append(Paragraph(f"<b>Version</b> {VERSION}", BODY))
    s.append(Paragraph(f"<b>Generated</b> {TODAY}", BODY))
    s.append(Paragraph("<b>License</b> MIT", BODY))
    s.append(Spacer(1, 0.3 * inch))
    s.append(
        para(
            '<i>"Persistent agency emerges when an AI system can convert memory into '
            'context and experience back into memory."</i>',
            NOTE,
        )
    )
    s.append(Spacer(1, 0.3 * inch))
    s.append(
        para(
            "This document is the implementation reference for CMA. It mirrors the code at "
            "v0.4.0 and supersedes prior whitepaper drafts (v0.1, v0.2). Every "
            "phase, command, schema, and design decision in the source repository is "
            "documented here."
        )
    )
    s.append(section_break())

    # ---- 1. executive summary ----
    s.append(para("1. Executive Summary", H1))
    s.append(para(
        "Most AI agents are stateless. They forget prior decisions, project conventions, "
        "what worked, and what failed. Standard RAG helps, but agent memory is relational and "
        "cumulative; the most useful context for a task is rarely the nearest vector chunk. "
        "It is a decision linked to a project, a postmortem linked to a failure mode, or a "
        "pattern inferred across tasks."
    ))
    s.append(para(
        "CMA is a lightweight memory layer each agent carries with it. The architecture is "
        "local-first, Obsidian-compatible, and built on three intelligent functions:"
    ))
    s.extend(bullets([
        "<b>Reasoner</b> &mdash; frames the goal, decides what context matters",
        "<b>Retriever</b> &mdash; converts long-term memory into task-specific context specs (graph + hybrid search)",
        "<b>Recorder</b> &mdash; converts completed work into structured, durable memory",
    ]))
    s.append(para(
        "v0.4.0 ships nine functional phases: skeleton, parser, graph, retrieval, recording, "
        "MCP server, evaluation, health observability, and lifecycle curation. The repository "
        "promise is unchanged: <i>add a persistent contextual memory layer to your agent without "
        "rewriting your agent.</i>"
    ))
    s.append(section_break())

    # ---- 2. core thesis ----
    s.append(para("2. Core Thesis", H1))
    s.append(para("2.1 Memory and context are different.", H2))
    s.append(para(
        "Memory is durable stored experience. Context is the temporary working set built for "
        "a specific task. The transformation between them is the architecture."
    ))
    s.append(code("memory -> context -> action -> experience -> memory"))
    s.append(para("2.2 Agent memory needs three intelligent functions.", H2))
    s.append(para(
        "Storage and retrieval are necessary but insufficient. The Reasoner decides what "
        "matters, the Retriever reconstructs it, and the Recorder formalizes new experience "
        "back into memory. All three must be first-class to compound intelligence over time."
    ))
    s.append(para("2.3 Context specs are the interface between memory and action.", H2))
    s.append(para(
        "Retrieval should not return a pile of chunks. It returns a structured, inspectable, "
        "testable artifact: the Context Spec. Fragments, relationship map, scores, "
        "provenance, retrieval parameters &mdash; all of it auditable."
    ))
    s.append(para("2.4 Learning happens in the loop.", H2))
    s.append(code("Frame -> Retrieve -> Reason -> Record -> Integrate -> Improve"))
    s.append(section_break())

    # ---- 3. lightweight + fractal ----
    s.append(para("3. Lightweight, Per-Agent, Fractal-by-Design", H1))
    s.append(para(
        "CMA is meant to be the memory layer a single agent carries with it &mdash; small enough "
        "that every agent in a system can have its own."
    ))
    s.append(para("3.1 Per-agent vaults are the unit.", H2))
    s.append(para(
        "An agent's vault holds its own decisions, sessions, patterns, and project context. "
        "Two agents working in the same system don't pollute each other's memory; their "
        "experiences stay separate unless explicitly shared. This is the default."
    ))
    s.append(para("3.2 The architecture is fractal.", H2))
    s.append(para(
        "A vault is a graph of notes. Nothing stops a vault itself from becoming a single "
        "node in a larger graph &mdash; a system-level or network-level memory graph that links "
        "agents instead of notes. The same primitives (graph traversal, hybrid search, "
        "fragment extraction, context spec assembly) apply at any scale."
    ))
    s.append(para("3.3 Future direction.", H2))
    s.append(para(
        "Multi-agent systems where the Retriever traverses across agent boundaries when "
        "context demands it. Cross-agent provenance. Network-wide pattern recognition. "
        "Selective memory federation: one agent loaning a slice of its graph to another for "
        "the duration of a task. v0.4 is the per-agent foundation; the fractal layer is on "
        "the roadmap (Phase 10+)."
    ))
    s.append(section_break())

    # ---- 4. architecture ----
    s.append(para("4. High-Level Architecture", H1))
    s.append(code(
        """Human / System Goal
       |
       v
  +------------+
  |  Reasoner  |  frames goal, judges risk, requests memory
  +------------+
       |
       v
  +------------+
  |  Retriever |  hybrid search + graph traversal + fragments
  +------------+
       |
   context_spec.md
       |
       v
  +------------+
  |  Reasoner  |  plans, acts, supervises, synthesises
  +------------+
       |
   completion_package
       |
       v
  +------------+
  |  Recorder  |  decisions, patterns, sessions, daily logs
  +------------+
       |
       v
  +------------+
  |  Retriever |  re-indexes, links, validates
  +------------+
       |
       v
   Better memory for the next task"""
    ))
    s.append(para("4.1 Component responsibilities", H2))
    s.append(make_table(
        ["Component", "Role"],
        [
            ["Reasoner", "Frames goals, decides what context is needed, supervises action, instructs Recorder."],
            ["Retriever", "Transforms the memory graph into task-specific Context Specs."],
            ["Recorder", "Transforms completed work into structured, retrievable memory records."],
            ["Vault", "Canonical local Obsidian-compatible markdown store."],
            [".cma/", "Rebuildable indexes, caches, graph state, embeddings, retrieval logs."],
        ],
    ))
    s.append(section_break())

    # ---- 5. project layout ----
    s.append(para("5. Project Layout", H1))
    s.append(code(
        """my-agent/
  cma.config.yaml
  README.md
  reasoner/
    prompts/  policies/  task_frames/  outputs/
  retriever/
    indexes/  specs/  graph_reports/  retrieval_logs/
  recorder/
    completion_packages/  memory_write_proposals/
    write_logs/  templates/
  vault/                       # canonical memory (Obsidian-compatible)
    000-inbox/
    001-projects/
    002-sessions/
    003-decisions/
    004-patterns/
    005-people/
    006-tools/
    007-codebase/
    008-context-specs/
    009-evals/
    010-daily-log/
    011-archive/
  .cma/                        # derived state, rebuildable
    graph/         (nodes.json)
    bm25/          (index.pkl)
    embeddings/    (embeddings.npy, doc_ids.json, meta.json)
    state/         (retrieval_log.jsonl)
    cache/  eval_runs/"""
    ))
    s.append(para(
        "<b>Vault is the source of truth.</b> Markdown notes, YAML frontmatter, wikilinks, "
        "human edits, recorded decisions. Everything in <code>.cma/</code> is derived: delete "
        "it and rebuild from the vault any time."
    ))
    s.append(section_break())

    # ---- 6. core schemas ----
    s.append(para("6. Core Data Schemas", H1))
    s.append(para(
        "All schemas are Pydantic v2 models defined in <code>cma/schemas/</code>."
    ))
    s.append(para("6.1 TaskFrame", H2))
    s.append(code("""TaskFrame:
  task_id:        string
  goal:           string
  domain:         string                 # default: "general"
  risk_level:     low | medium | high    # default: medium
  requires_memory: bool                  # default: true
  context_request:
    query:        string
    max_tokens:   int (default 8000)
    max_depth:    int (default 2)
    beam_width:   int (default 5)
    include:      list[string]
    exclude:      list[string]
  constraints:    list[string]
  expected_output: list[string]"""))
    s.append(para("6.2 ContextSpec", H2))
    s.append(code("""ContextSpec:
  spec_id:        string
  task_id:        string
  query:          string
  generated_at:   datetime (UTC)
  retriever_version: string
  parameters:     dict
  fragments:      list[Fragment]
  relationship_map: list[RelationshipEdge]
  open_questions: list[string]
  exclusions:     list[Exclusion]

Fragment:
  source_node:    string         # human-readable note title
  node_type:      string         # decision / pattern / session / note / ...
  node_score:     float          # final hybrid score after boost + decay
  fragment_score: float          # paragraph-level relevance
  depth:          int            # 0 = seed, >0 = reached via traversal
  text:           string
  why_included:   string"""))
    s.append(para("6.3 CompletionPackage", H2))
    s.append(code("""CompletionPackage:
  task_id:    string
  goal:       string
  summary:    string
  outputs:    list[string]
  decisions:  list[Decision]
  patterns:   list[Pattern]
  context_usage:
    high_value: list[string]
    low_value:  list[string]
    missing:    list[string]
  human_feedback: string

Decision:
  title:      string
  status:     proposed | accepted | rejected | superseded
  confidence: float (0.0-1.0)
  rationale:  string

Pattern:
  title:      string
  confidence: float
  evidence:   list[string]"""))
    s.append(para("6.4 MemoryRecord", H2))
    s.append(code("""MemoryRecord:                     # in-memory projection of a vault note
  record_id:      string         # filename stem
  type:           string         # session / decision / pattern / note / ...
  title:          string
  path:           string         # relative to vault/
  created_at:     datetime | None
  task_id:        string | None
  domain:         string | None
  confidence:     float | None
  status:         draft | active | proposed | accepted | rejected
                | superseded | archived
  links:          list[string]   # wikilink targets
  tags:           list[string]
  human_verified: bool
  body:           string
  frontmatter:    dict"""))
    s.append(section_break())

    # ---- 7. phases 1-9 ----
    s.append(para("7. Implementation Phases", H1))
    s.append(para(
        "All nine phases are implemented and covered by the test suite (150 tests at v0.4.0). "
        "Each subsection covers what shipped, the relevant modules, and the public API."
    ))

    s.append(para("7.1 Phase 1: Skeleton, schemas, config, CLI", H2))
    s.extend(bullets([
        "Pydantic v2 schemas (<code>cma/schemas/</code>): TaskFrame, ContextSpec, CompletionPackage, MemoryRecord",
        "Configuration loader (<code>cma/config.py</code>): <code>cma.config.yaml</code> with retrieval and recorder sections",
        "Typer-based CLI (<code>cma/cli.py</code>) with <code>cma init</code> and <code>cma version</code>",
        "Project scaffolding: vault folders 000-inbox through 011-archive; node folders for reasoner/retriever/recorder",
    ]))

    s.append(para("7.2 Phase 2: Markdown vault parser", H2))
    s.extend(bullets([
        "<code>cma/storage/markdown_store.py</code>: <code>parse_vault()</code>, <code>parse_note()</code>, <code>walk_vault()</code>, <code>extract_wikilinks()</code>",
        "Wikilink regex strips aliases and headers: <code>[[Note]]</code>, <code>[[Note#Section]]</code>, <code>[[Note|alias]]</code> all resolve to <code>Note</code>",
        "YAML frontmatter parsed via python-frontmatter; unknown <code>type</code> falls back to <code>note</code>; unknown <code>status</code> falls back to <code>active</code>",
        "MemoryRecord projection holds body, frontmatter, links, status, tags, confidence",
    ]))

    s.append(para("7.3 Phase 3: Graph index + health", H2))
    s.extend(bullets([
        "<code>cma/storage/graph_store.py</code>: NetworkX DiGraph keyed by record_id",
        "Wikilink resolution: title match (case-insensitive) &rarr; record_id match &rarr; placeholder node with exists=False",
        "<code>graph_health_report()</code>: total nodes, edges, orphans, broken links, type breakdown",
        "<code>cma graph health</code> CLI command",
    ]))

    s.append(para("7.4 Phase 4: Hybrid retrieval", H2))
    s.extend(bullets([
        "<code>cma/retriever/lexical.py</code>: BM25L (not BM25Okapi &mdash; see ADR section). Title repeated 3x to weight it.",
        "<code>cma/retriever/embeddings.py</code>: pluggable Embedder protocol; SentenceTransformerEmbedder and OpenAIEmbedder built-in (lazy-imported)",
        "<code>cma/retriever/scoring.py</code>: hybrid score (alpha * sem + (1-alpha) * lex), metadata boosts, depth decay",
        "<code>cma/retriever/traversal.py</code>: beam-pruned BFS over outgoing AND incoming edges",
        "<code>cma/retriever/fragments.py</code>: paragraph-level extraction with cross-node Jaccard dedup",
        "<code>cma/retriever/spec_builder.py</code>: ContextSpec assembly + markdown rendering",
        "<code>cma/retriever/retriever.py</code>: top-level orchestrator. <code>Retriever.from_project(path).retrieve(query)</code>",
        "<code>cma index</code>: persists nodes.json, BM25 pickle, embedding matrix to <code>.cma/</code>",
        "<code>cma retrieve \"...\"</code>: emits the markdown spec; <code>--json</code>, <code>--save</code>, <code>--max-depth</code> flags",
    ]))

    s.append(para("7.4.1 Scoring formula", H3))
    s.append(code("""node_score   = alpha * semantic_score + (1 - alpha) * lexical_score
final_score  = node_score * metadata_boost(record) * (depth_decay ** depth)

defaults: alpha=0.7  node_threshold=0.30  fragment_threshold=0.42
          depth_decay=0.80  beam_width=5  max_depth=2  max_fragments_per_node=3

metadata boosts:
  accepted decision      +0.10
  superseded decision    -0.50
  rejected decision      -0.30
  human_verified         +0.10
  confidence >= 0.85     +0.08
  confidence <  0.30     -0.10
  status archived        -0.20"""))

    s.append(para("7.5 Phase 5: Recorder", H2))
    s.extend(bullets([
        "<code>cma/recorder/policy.py</code>: WRITE/DRAFT/PROPOSE/SKIP routing by status + confidence",
        "<code>cma/recorder/templates.py</code>: markdown templates for session, decision, pattern, daily-log",
        "<code>cma/recorder/writers.py</code>: file writers with sanitize_filename, duplicate detection",
        "<code>cma/recorder/recorder.py</code>: <code>Recorder.from_project()</code>, <code>record_completion()</code>, <code>load_completion_package()</code>",
        "Always writes a session note + appends a daily-log entry; decisions and patterns gated by policy",
        "Duplicate detection by sanitized title; matching files in vault are skipped (not overwritten)",
        "JSONL audit trail at <code>recorder/write_logs/&lt;task_id&gt;-write-log.jsonl</code>",
        "<code>cma record &lt;package.yaml&gt;</code> CLI with <code>--dry-run</code>",
    ]))

    s.append(para("7.5.1 Memory write policy", H3))
    s.append(code("""decision rules:
  status accepted/rejected   -> WRITE
  status proposed
    confidence >= 0.75       -> WRITE
    confidence >= 0.50       -> DRAFT (status=draft)
    confidence >= 0.25       -> PROPOSE (recorder/memory_write_proposals/)
  status superseded          -> WRITE (or PROPOSE if configured)
  any < 0.25                 -> SKIP

pattern rules:
  confidence >= 0.75         -> WRITE
  confidence >= 0.50         -> DRAFT (or PROPOSE if low_confidence_pattern in config)
  confidence >= 0.25         -> PROPOSE
  any < 0.25                 -> SKIP

require_human_approval_for (config knob, default):
  - autonomy_change
  - low_confidence_pattern
  - supersede_decision"""))

    s.append(para("7.6 Phase 6: MCP server", H2))
    s.extend(bullets([
        "<code>cma/mcp/server.py</code>: FastMCP-based server, stdio transport",
        "Optional install: <code>pip install 'contextual-memory-architecture[mcp]'</code>",
        "<code>cma mcp serve --project &lt;path&gt;</code> launches the server",
        "Six fine-grained graph primitives + four higher-level orchestrators (10 tools total)",
    ]))
    s.append(para("7.6.1 The 10 MCP tools", H3))
    s.append(make_table(
        ["Tool", "Purpose"],
        [
            ["search_notes", "Hybrid BM25 + embedding search, returns top_k matches"],
            ["get_note", "Fetch a note's full body, frontmatter, links by title or stem"],
            ["get_outgoing_links", "Notes this note links TO via wikilinks"],
            ["get_backlinks", "Notes that link to this note"],
            ["traverse_graph", "BFS within N hops of a start note"],
            ["search_by_frontmatter", "Filter notes by YAML metadata key/value"],
            ["retrieve", "Full Retriever pipeline -> rendered markdown Context Spec"],
            ["record_completion", "Recorder ingestion (YAML string -> vault writes)"],
            ["graph_health", "Structural health report"],
            ["reindex", "Rebuild in-memory Retriever/Recorder state"],
        ],
    ))
    s.append(para("7.6.2 Claude Code integration snippet", H3))
    s.append(code("""// ~/.claude/mcp.json
{
  "mcpServers": {
    "cma": {
      "command": "cma",
      "args": ["mcp", "serve", "--project", "/absolute/path/to/your/cma-project"]
    }
  }
}"""))

    s.append(para("7.7 Phase 7: Evaluation harness", H2))
    s.extend(bullets([
        "<code>cma/evals/metrics.py</code>: Recall@k, Precision@k, MRR, Memory Usefulness Score, Context Efficiency Score",
        "<code>cma/evals/runner.py</code>: BenchmarkQuery, BenchmarkResult, BenchmarkRun, RetrievalMode enum",
        "Four modes: NO_MEMORY, VECTOR_ONLY, GRAPHRAG, FULL_CMA",
        "<code>cma evals run &lt;benchmark.yaml&gt; --mode graphrag --save out.json</code>",
        "Sample benchmark at <code>examples/benchmark.yaml</code>",
    ]))
    s.append(para("7.7.1 Memory Usefulness Score formula", H3))
    s.append(code("""MUS = +2.0 * relevant_used
      +2.0 * prior_decision_applied
      +2.0 * prior_failure_avoided
      -1.0 * irrelevant_included
      -3.0 * critical_missed
      -2.0 * stale_or_superseded_used"""))

    s.append(para("7.8 Phase 8: Memory health + observability", H2))
    s.extend(bullets([
        "<code>cma/health/report.py</code>: <code>health_report()</code> returns dict with vault, indexes, graph, retrieval sub-reports",
        "Soft thresholds: vault > 50K notes, embeddings > 200 MB, orphan rate > 30%, broken-link rate > 5%, never-retrieved > 70%",
        "<code>log_retrieval()</code> appends per-event JSON to <code>.cma/state/retrieval_log.jsonl</code>",
        "Retriever auto-logs every <code>retrieve()</code> call (best-effort, won't break retrieval if log dir is bad)",
        "<code>cma retrieve</code> emits a context budget gauge: <code>[#######-----]  1,847 / 8,000 tokens (23%)</code>",
        "<code>cma health [--json]</code> CLI command with rich tables",
    ]))

    s.append(para("7.9 Phase 9: Memory lifecycle", H2))
    s.extend(bullets([
        "<code>cma/lifecycle/archive.py</code>: <code>archive_note()</code>, <code>archive_cold_notes()</code>",
        "<code>cma/lifecycle/supersede.py</code>: <code>supersede_decision()</code>",
        "<code>cma archive --type pattern --older-than 90 [--dry-run]</code>",
        "<code>cma supersede \"Old Decision\" --by \"New Decision\"</code>",
        "Archive moves files into <code>vault/011-archive/</code> and sets frontmatter <code>status: archived</code>, <code>archived_at: &lt;iso&gt;</code>",
        "Cold-ness = (last_retrieval older than N days) OR (no log entry AND <code>created</code> frontmatter older than N days). No signal &rarr; skipped.",
        "Filename collisions handled by suffix: <code>&lt;stem&gt;-archived-YYYYMMDD-HHMMSS.md</code>",
        "Supersede updates frontmatter (<code>status</code>, <code>superseded_by</code>, <code>superseded_at</code>) AND appends <code>**Superseded by [[New]].**</code> to the body",
    ]))
    s.append(section_break())

    # ---- 8. CLI reference ----
    s.append(para("8. CLI Reference", H1))
    s.append(make_table(
        ["Command", "Description"],
        [
            ["cma init <path>", "Scaffold a new project (vault folders, node folders, .cma/, default config)"],
            ["cma setup [path]", "Interactive: choose agent integration + embedding provider"],
            ["cma index [path] [--no-embeddings]", "Training phase: parse vault, build graph, BM25, embeddings"],
            ["cma graph health [path]", "Graph structure report"],
            ["cma retrieve \"<query>\" [--project p] [--max-depth N] [--save P] [--json]", "Run Retriever, print/save Context Spec, show context budget gauge"],
            ["cma record <package.yaml> [--project p] [--dry-run]", "Recorder ingestion"],
            ["cma evals run <bench.yaml> [--mode M] [--save out.json]", "Benchmark suite runner"],
            ["cma mcp serve [--project p]", "Start MCP server over stdio"],
            ["cma health [--json]", "Memory health: vault, indexes, graph, retrieval activity"],
            ["cma archive [--type T] [--status S] [--older-than D] [--dry-run]", "Archive cold notes"],
            ["cma supersede \"Old\" --by \"New\" [--dry-run]", "Mark old as superseded by new"],
            ["cma version", "Print installed version"],
        ],
    ))
    s.append(section_break())

    # ---- 9. config reference ----
    s.append(para("9. Configuration Reference (cma.config.yaml)", H1))
    s.append(code("""vault_path: ./vault                # canonical memory location
index_path: ./.cma                  # derived state location
embedding_provider: sentence-transformers
                                    # options: sentence-transformers | openai | none
embedding_model: all-MiniLM-L6-v2  # provider-specific model name

retrieval:
  alpha: 0.7                        # 0=lexical only, 1=semantic only
  max_depth: 2                      # graph traversal hops
  beam_width: 5                     # candidates kept per depth
  node_threshold: 0.30              # seed score floor (NOT applied to traversed nodes)
  fragment_threshold: 0.42          # paragraph score floor (depth > 0 only)
  depth_decay: 0.80                 # final_score *= decay**depth
  max_fragments_per_node: 3

recorder:
  require_human_approval_for:
    - autonomy_change
    - low_confidence_pattern
    - supersede_decision
  default_confidence: 0.60"""))
    s.append(section_break())

    # ---- 10. ADRs ----
    s.append(para("10. Architectural Decisions", H1))
    s.append(para("10.1 BM25L over BM25Okapi", H2))
    s.append(para(
        "Initial implementation used BM25Okapi. Its IDF formula goes to zero or negative when "
        "a term appears in more than half the documents &mdash; a degenerate case in our corpus "
        "because wikilink anchor text duplicates terms across linked notes. BM25Plus avoids the "
        "negative IDF but introduces a delta term that gives every doc a non-zero baseline, "
        "which our threshold-based filtering treated as false positives. <b>BM25L</b> uses "
        "<code>log((N+1)/(df+0.5))</code> &mdash; always positive, but zero-floor for docs with no "
        "query terms. This is the right shape for graph-derived corpora."
    ))
    s.append(para("10.2 node_threshold applies to seeds, not traversed nodes", H2))
    s.append(para(
        "The whitepaper section 14 lists node_threshold as a final filter. In our 4-doc test "
        "vault, a graph-linked pattern (Queue Retry Pattern) at depth 1 from a strong seed "
        "consistently scored below 0.30 because it had no direct query overlap &mdash; only the "
        "wikilink mention earned its place. Filtering it would defeat the entire point of "
        "GraphRAG. Resolution: <b>node_threshold gates seed selection only.</b> Traversed "
        "nodes earn inclusion via graph adjacency; beam_width and max_depth control volume."
    ))
    s.append(para("10.3 Title repetition for BM25", H2))
    s.append(para(
        "Tokenization concatenates the title 3x before the body. Cheap way to give title "
        "tokens a stronger BM25 signal without learning a separate field-weighted index. "
        "Plays well with BM25L's TF-saturation behavior."
    ))
    s.append(para("10.4 Vault is canonical, .cma/ is rebuildable", H2))
    s.append(para(
        "Memory must survive index corruption, version upgrades, and tool changes. Markdown "
        "with YAML frontmatter and wikilinks is the spec. Embeddings, BM25 pickles, graph "
        "JSON, and retrieval logs all live under <code>.cma/</code> and can be wiped + "
        "rebuilt by <code>cma index</code>."
    ))
    s.append(para("10.5 Per-agent vaults, fractal-by-design", H2))
    s.append(para(
        "Default to one vault per agent &mdash; no shared global brain &mdash; so experiences don't "
        "cross-contaminate. The local-first markdown design is what makes the fractal "
        "framing tractable: a vault is a portable artifact, an MCP server is a portable "
        "interface, and a graph of vaults is just another graph."
    ))
    s.append(section_break())

    # ---- 11. memory at scale ----
    s.append(para("11. Memory at Scale", H1))
    s.append(para(
        "You cannot have infinite learned memory. CMA addresses this with health "
        "observability (Phase 8) plus explicit curation (Phase 9). Realistic "
        "single-vault projections on a typical laptop:"
    ))
    s.append(make_table(
        ["Vault size", "Markdown", "Embeddings (384d)", "RAM", "Query latency"],
        [
            ["1K notes",   "~10 MB",  "~1.5 MB",   "~50 MB",   "<50 ms"],
            ["10K notes",  "~100 MB", "~15 MB",    "~250 MB",  "<100 ms"],
            ["100K notes", "~1 GB",   "~150 MB",   "~1.5 GB",  "~500 ms"],
            ["1M notes",   "~10 GB",  "~1.5 GB",   "~10+ GB",  "seconds; needs ANN"],
        ],
    ))
    s.append(para(
        "When a single agent's vault crosses practical thresholds, the answer is to <b>shard "
        "by domain</b> (the fractal pattern) or <b>archive cold notes</b> (Phase 9). The "
        "automation is intentionally simple in v0.4 &mdash; you decide what's cold &mdash; because "
        "auto-archival policy decisions need to be the agent owner's, not the framework's."
    ))
    s.append(section_break())

    # ---- 12. roadmap ----
    s.append(para("12. Roadmap (Phase 10+)", H1))
    s.extend(bullets([
        "<b>Cluster consolidation.</b> Run Leiden clustering on the graph; LLM-summarize each cluster; prepend the relevant cluster summary to context specs. Tighter context for global-synthesis queries.",
        "<b>Vault sharding.</b> Auto-split by domain when a single vault crosses size thresholds; federate retrieval across shards.",
        "<b>Decay scoring.</b> Optional metadata boost that penalizes notes by age-since-last-retrieval; off by default.",
        "<b>Cross-agent retrieval (the fractal layer).</b> Each agent's vault becomes a node in a higher-order graph; selective memory federation between agents.",
        "<b>Typed graph edges beyond wikilinks.</b> caused-by, supersedes, dependency, contradicts &mdash; first-class edge types with type-aware scoring.",
        "<b>Memory provenance enforcement.</b> Every record answers: where did it come from, when, by whom or what, was it human-verified, has it been superseded.",
        "<b>HTTP+SSE MCP transport.</b> For remote Claude.ai connectors and hosted agent runtimes.",
        "<b>Deprecated.</b> None at v0.4. Whitepaper drafts v0.1 and v0.2 are superseded by this document.",
    ]))
    s.append(section_break())

    # ---- 13. glossary ----
    s.append(para("13. Glossary", H1))
    s.append(make_table(
        ["Term", "Definition"],
        [
            ["CMA", "Contextual Memory Architecture."],
            ["Reasoner", "Judgment node; frames tasks, requests context, instructs writes."],
            ["Retriever", "Recall node; turns memory into Context Specs via hybrid + graph search."],
            ["Recorder", "Memory formation node; turns CompletionPackages into vault writes."],
            ["Memory", "Durable stored experience (markdown notes in the vault)."],
            ["Context", "Temporary working set built for a specific task."],
            ["Context spec", "Structured artifact: fragments + relationship map + scores + provenance."],
            ["Memory graph", "Graph of notes linked by wikilinks; nodes carry frontmatter as metadata."],
            ["Vault", "Local Obsidian-compatible markdown directory. Canonical memory store."],
            ["Training phase", "The cma index step: parse vault, build graph, BM25, embeddings."],
            ["GraphRAG", "Retrieval that uses graph structure (not just vector similarity)."],
            ["MCP", "Model Context Protocol. JSON-RPC interface for agents to call tools."],
            ["MUS", "Memory Usefulness Score. Weighted retrieval-quality metric."],
            ["CES", "Context Efficiency Score. used_fragments / included_fragments."],
        ],
    ))
    s.append(Spacer(1, 0.3 * inch))
    s.append(para(
        "<i>End of whitepaper. Repository: github.com/danny-watkins/contextual-memory-architecture</i>",
        BODY,
    ))

    return s


def main() -> None:
    doc = BaseDocTemplate(
        str(OUT),
        pagesize=LETTER,
        leftMargin=inch * 0.85,
        rightMargin=inch * 0.85,
        topMargin=inch * 0.75,
        bottomMargin=inch * 0.75,
        title=TITLE,
        author="Danny Watkins",
        subject="Contextual Memory Architecture - Technical Whitepaper",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
    )
    doc.addPageTemplates([
        PageTemplate(id="first", frames=[frame], onPage=_on_first_page),
        PageTemplate(id="rest", frames=[frame], onPage=_on_page),
    ])
    story = build_story()
    doc.build(story)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

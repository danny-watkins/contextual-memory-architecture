"""Generate the CMA technical whitepaper PDF.

Matches the visual style of the v0.1/v0.2 reference whitepapers: white pages,
teal headers, clean sans-serif body, numbered sections.

Run from repo root:
    python docs/build_whitepaper.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).parent / "CMA_Whitepaper_v0.4.pdf"
VERSION = "0.4"
TITLE = "Contextual Memory Architecture"
SUBTITLE = "A Lightweight, Local-First Memory Layer for Persistent AI Agents"
SUBSUBTITLE = "Technical Whitepaper and Implementation Reference - Version 0.4"
TODAY = date.today().isoformat()

# ----- palette: match the v0.2 reference whitepaper -----
TEAL = colors.HexColor("#2C7884")      # primary header / accent
TEAL_LIGHT = colors.HexColor("#5da6b3")
TEAL_BG = colors.HexColor("#e8f1f3")   # subtle teal tint for callouts
TEXT = colors.HexColor("#1f1f1f")
DIM = colors.HexColor("#666666")
ROW_ALT = colors.HexColor("#f4f6f7")
CODE_BG = colors.HexColor("#f5f5f5")
RULE = colors.HexColor("#cfd8db")

# ----- styles -----
ss = getSampleStyleSheet()

T_TITLE = ParagraphStyle(
    "TTitle", parent=ss["Title"], fontName="Helvetica-Bold",
    fontSize=32, leading=38, alignment=TA_CENTER, spaceAfter=10,
    textColor=TEAL,
)
T_SUB = ParagraphStyle(
    "TSub", parent=ss["Normal"], fontName="Helvetica-Oblique",
    fontSize=14, leading=20, alignment=TA_CENTER, spaceAfter=4,
    textColor=TEXT,
)
T_SUBSUB = ParagraphStyle(
    "TSubsub", parent=ss["Normal"], fontName="Helvetica",
    fontSize=10, leading=14, alignment=TA_CENTER, spaceAfter=24,
    textColor=DIM,
)
T_QUOTE = ParagraphStyle(
    "TQuote", parent=ss["Normal"], fontName="Helvetica-Oblique",
    fontSize=12, leading=18, alignment=TA_CENTER,
    textColor=TEXT, spaceBefore=20, spaceAfter=20,
    leftIndent=48, rightIndent=48,
)
T_META = ParagraphStyle(
    "TMeta", parent=ss["Normal"], fontName="Helvetica",
    fontSize=10, leading=15, alignment=TA_CENTER, textColor=DIM,
    spaceAfter=4,
)
H1 = ParagraphStyle(
    "H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
    fontSize=18, leading=24, spaceBefore=14, spaceAfter=8,
    textColor=TEAL,
)
H2 = ParagraphStyle(
    "H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
    fontSize=13, leading=18, spaceBefore=12, spaceAfter=4,
    textColor=TEAL,
)
H3 = ParagraphStyle(
    "H3", parent=ss["Heading3"], fontName="Helvetica-Bold",
    fontSize=11, leading=15, spaceBefore=8, spaceAfter=2,
    textColor=TEXT,
)
BODY = ParagraphStyle(
    "Body", parent=ss["Normal"], fontName="Helvetica",
    fontSize=10.5, leading=15, alignment=TA_LEFT,
    spaceAfter=8, textColor=TEXT,
)
BULLET = ParagraphStyle(
    "Bullet", parent=BODY, leftIndent=20, bulletIndent=8, spaceAfter=4,
)
CODE = ParagraphStyle(
    "Code", parent=ss["Code"], fontName="Courier",
    fontSize=8.5, leading=11.5,
    backColor=CODE_BG, borderColor=RULE, borderWidth=0.4,
    borderPadding=8, leftIndent=2, rightIndent=2,
    spaceAfter=10, spaceBefore=4, textColor=TEXT,
)
CALLOUT = ParagraphStyle(
    "Callout", parent=BODY, fontName="Helvetica-Oblique",
    backColor=TEAL_BG, borderColor=TEAL_LIGHT, borderWidth=0.4,
    borderPadding=8, leftIndent=4, rightIndent=4,
    spaceBefore=4, spaceAfter=10, textColor=TEXT,
)


# ----- page chrome -----


def _on_page(canvas, doc):
    canvas.saveState()
    # Footer rule
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(inch * 0.9, inch * 0.65, LETTER[0] - inch * 0.9, inch * 0.65)
    # Footer text
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(DIM)
    canvas.drawString(inch * 0.9, inch * 0.45,
                      f"Contextual Memory Architecture (CMA) - v{VERSION}")
    canvas.drawRightString(LETTER[0] - inch * 0.9, inch * 0.45, str(doc.page))
    canvas.restoreState()


def _on_first_page(canvas, doc):
    canvas.saveState()
    # Top decorative band
    canvas.setFillColor(TEAL)
    canvas.rect(0, LETTER[1] - 0.3 * inch, LETTER[0], 0.3 * inch, fill=1, stroke=0)
    # Bottom band
    canvas.setFillColor(TEAL)
    canvas.rect(0, 0, LETTER[0], 0.25 * inch, fill=1, stroke=0)
    # Footer text
    canvas.setFillColor(DIM)
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(LETTER[0] / 2, inch * 0.45,
                             f"Contextual Memory Architecture (CMA) - v{VERSION}")
    canvas.restoreState()


# ----- helpers -----


def code(text: str) -> Preformatted:
    return Preformatted(text.strip("\n"), CODE)


def para(text: str, style=BODY) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: list[str]) -> list:
    return [Paragraph(f"&bull;&nbsp;&nbsp; {t}", BULLET) for t in items]


def section_break() -> PageBreak:
    return PageBreak()


def teal_rule() -> HRFlowable:
    return HRFlowable(width="100%", thickness=1.2, color=TEAL,
                      spaceBefore=2, spaceAfter=10)


def make_table(headers: list[str], rows: list[list[str]]) -> Table:
    data = [headers] + rows
    t = Table(data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                # Header row: teal background, white text
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                # Body
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9.5),
                ("TEXTCOLOR", (0, 1), (-1, -1), TEXT),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE),
            ]
        )
    )
    return t


# ----- content -----


def build_story() -> list:
    s: list = []

    # ---------- title page ----------
    s.append(Spacer(1, 1.6 * inch))
    s.append(Paragraph(TITLE, T_TITLE))
    s.append(Paragraph("(CMA)", T_TITLE))
    s.append(Spacer(1, 0.15 * inch))
    s.append(Paragraph(SUBTITLE, T_SUB))
    s.append(Paragraph(SUBSUBTITLE, T_SUBSUB))

    s.append(Spacer(1, 0.4 * inch))
    s.append(Paragraph(
        "<i>Persistent agency emerges when an AI system can convert memory "
        "into context and experience back into memory.</i>",
        T_QUOTE,
    ))

    s.append(Spacer(1, 1.0 * inch))
    s.append(Paragraph(f"Version {VERSION}", T_META))
    s.append(Paragraph(f"Generated {TODAY}", T_META))
    s.append(Paragraph("MIT License", T_META))
    s.append(Paragraph(
        "github.com/danny-watkins/contextual-memory-architecture", T_META
    ))
    s.append(section_break())

    # ---------- abstract ----------
    s.append(Paragraph("Abstract", H1))
    s.append(teal_rule())
    s.append(para(
        "Most AI agents remain functionally stateless. They can perform impressive work "
        "inside a single context window, but they struggle to carry experience forward "
        "across tasks, sessions, projects, teams, and time. Existing approaches often "
        "treat memory as a storage or retrieval problem: save facts, embed chunks, "
        "retrieve similar text, and append it to a prompt. This helps, but it does not "
        "fully solve the agent-memory problem."
    ))
    s.append(para(
        "Contextual Memory Architecture (CMA) proposes a modular, local-first memory "
        "layer for persistent AI agents. CMA is centered on a local Obsidian-compatible "
        "vault and three intelligent nodes: the Reasoner, the Retriever, and the "
        "Recorder. The Reasoner frames goals and decides what context matters. The "
        "Retriever converts long-term memory into task-specific context specs using "
        "hybrid search, graph traversal, fragment extraction, and provenance. The "
        "Recorder converts completed work into structured, durable memory that improves "
        "future retrieval."
    ))
    s.append(para(
        "CMA is open-source, framework-agnostic, and designed as a lightweight memory "
        "layer each agent in a system can carry with it. The repository promise: "
        "<i>add a persistent contextual memory layer to your agent without rewriting "
        "your agent.</i>"
    ))
    s.append(code("Goal -> Reason -> Retrieve -> Context -> Act -> Record -> Re-index -> Better future context"))
    s.append(section_break())

    # ---------- 1. motivation ----------
    s.append(Paragraph("1. Motivation", H1))
    s.append(teal_rule())

    s.append(para("1.1 The Stateless Agent Problem", H2))
    s.append(para(
        "Agents without durable memory pay the same context-gathering cost on every "
        "task. They forget prior decisions, failed approaches, project conventions, "
        "user preferences, tool behavior, and recurring constraints. As a result, they "
        "do not compound the way a capable human collaborator does."
    ))

    s.append(para("1.2 The Limits of Simple RAG", H2))
    s.append(para(
        "Simple retrieval-augmented generation is useful, but agent memory is "
        "relational, temporal, and cumulative. The most important context may not be "
        "the nearest vector chunk. It may be a decision linked to a project, a "
        "postmortem linked to a failure mode, a pattern inferred across tasks, or a "
        "superseded decision that should be excluded."
    ))
    s.append(para(
        "CMA treats retrieval as <i>contextual reconstruction</i>, not chunk lookup. "
        "The Retriever traverses relationships, applies metadata filters, selects "
        "fragments, preserves provenance, and assembles an artifact the Reasoner "
        "can use."
    ))

    s.append(para("1.3 The Missing Write Path", H2))
    s.append(para(
        "Many memory systems focus on retrieval. Fewer focus on recording. But a "
        "system that retrieves without recording does not compound. CMA treats memory "
        "writing as a first-class function. The Recorder is not a transcript logger. "
        "It is the memory formation layer."
    ))
    s.append(section_break())

    # ---------- 2. core thesis ----------
    s.append(Paragraph("2. Core Thesis", H1))
    s.append(teal_rule())
    s.extend(bullets([
        "<b>Memory and context are different.</b> Memory is durable stored experience; context is the temporary working set needed for a specific task.",
        "<b>Agent memory needs three intelligent functions.</b> Deciding what matters, retrieving what is known, and recording what should be remembered.",
        "<b>Context specs are the interface between memory and action.</b> The output of retrieval should be structured, inspectable, and testable.",
        "<b>Learning happens in the loop.</b> The system improves when Recorder-written memory becomes useful Retriever context for later Reasoner decisions.",
    ]))
    s.append(Spacer(1, 0.1 * inch))
    s.append(code(
        "Reasoner   = judgment and task framing\n"
        "Retriever  = contextual recall and context-spec assembly\n"
        "Recorder   = memory formation and write-back"
    ))
    s.append(section_break())

    # ---------- 3. lightweight + fractal ----------
    s.append(Paragraph("3. Lightweight, Per-Agent, Fractal-by-Design", H1))
    s.append(teal_rule())
    s.append(para(
        "CMA is meant to be the memory layer a single agent carries with it. Small "
        "enough that every agent in a system can have its own."
    ))
    s.append(para("3.1 Per-Agent Vaults Are the Unit", H2))
    s.append(para(
        "An agent's vault holds its own decisions, sessions, patterns, and project "
        "context. Two agents working in the same system don't pollute each other's "
        "memory; their experiences stay separate unless explicitly shared. This is "
        "the default."
    ))
    s.append(para("3.2 The Architecture is Fractal", H2))
    s.append(para(
        "A vault is a graph of notes. Nothing stops a vault itself from becoming a "
        "single node in a larger graph - a system-level or network-level memory graph "
        "that links agents instead of notes. The same primitives (graph traversal, "
        "hybrid search, fragment extraction, context spec assembly) apply at any scale."
    ))
    s.append(para("3.3 Future Direction", H2))
    s.append(para(
        "Multi-agent systems where the Retriever traverses across agent boundaries when "
        "context demands it. Cross-agent provenance. Network-wide pattern recognition. "
        "Selective memory federation: one agent loaning a slice of its graph to another "
        "for the duration of a task. v0.4 is the per-agent foundation; the fractal "
        "layer is on the roadmap."
    ))
    s.append(section_break())

    # ---------- 4. architecture ----------
    s.append(Paragraph("4. High-Level Architecture", H1))
    s.append(teal_rule())
    s.append(code(
        "Human / System Goal\n"
        "        |\n"
        "        v\n"
        "  [ Reasoner ]   frames goal, judges risk, requests memory\n"
        "        |\n"
        "        v\n"
        "  [ Retriever ]  hybrid search + graph traversal + fragments\n"
        "        |\n"
        "   context_spec.md\n"
        "        |\n"
        "        v\n"
        "  [ Reasoner ]   plans, acts, supervises, synthesises\n"
        "        |\n"
        "   completion_package\n"
        "        |\n"
        "        v\n"
        "  [ Recorder ]   decisions, patterns, sessions, daily logs\n"
        "        |\n"
        "        v\n"
        "  [ Retriever ]  re-indexes, links, validates\n"
        "        |\n"
        "        v\n"
        "  Better memory for the next task"
    ))
    s.append(make_table(
        ["Component", "Role"],
        [
            ["Reasoner",  "Frames goals, decides what context is needed, supervises action, instructs the Recorder."],
            ["Retriever", "Transforms the memory graph into task-specific Context Specs."],
            ["Recorder",  "Transforms completed work into structured, retrievable memory records."],
            ["Vault",     "Canonical local Obsidian-compatible markdown store."],
            [".cma/",     "Rebuildable indexes, caches, graph state, embeddings, retrieval logs."],
        ],
    ))
    s.append(section_break())

    # ---------- 5. project layout ----------
    s.append(Paragraph("5. Project Layout", H1))
    s.append(teal_rule())
    s.append(code(
        "my-agent/\n"
        "  cma.config.yaml\n"
        "  README.md\n"
        "  reasoner/    prompts/  policies/  task_frames/  outputs/\n"
        "  retriever/   indexes/  specs/    graph_reports/  retrieval_logs/\n"
        "  recorder/    completion_packages/  memory_write_proposals/\n"
        "               write_logs/  templates/\n"
        "  vault/                       # canonical memory (Obsidian-compatible)\n"
        "    000-inbox/        001-projects/     002-sessions/\n"
        "    003-decisions/    004-patterns/     005-people/\n"
        "    006-tools/        007-codebase/     008-context-specs/\n"
        "    009-evals/        010-daily-log/    011-archive/\n"
        "  .cma/                        # derived state, rebuildable\n"
        "    graph/         (nodes.json)\n"
        "    bm25/          (index.pkl)\n"
        "    embeddings/    (embeddings.npy, doc_ids.json, meta.json)\n"
        "    state/         (retrieval_log.jsonl)"
    ))
    s.append(Paragraph(
        "Vault is the source of truth. Markdown notes, YAML frontmatter, wikilinks, "
        "human edits, recorded decisions. Everything in <font name='Courier'>.cma/</font> is "
        "derived: delete it and rebuild from the vault any time.",
        CALLOUT,
    ))
    s.append(section_break())

    # ---------- 6. core schemas ----------
    s.append(Paragraph("6. Core Data Schemas", H1))
    s.append(teal_rule())
    s.append(para(
        "All schemas are Pydantic v2 models defined in <font name='Courier'>cma/schemas/</font>."
    ))

    s.append(para("6.1 TaskFrame", H2))
    s.append(code(
        "TaskFrame:\n"
        "  task_id:        string\n"
        "  goal:           string\n"
        "  domain:         string                 # default: \"general\"\n"
        "  risk_level:     low | medium | high    # default: medium\n"
        "  requires_memory: bool                  # default: true\n"
        "  context_request:\n"
        "    query:        string\n"
        "    max_tokens:   int (default 8000)\n"
        "    max_depth:    int (default 2)\n"
        "    beam_width:   int (default 5)\n"
        "  constraints:    list[string]\n"
        "  expected_output: list[string]"
    ))

    s.append(para("6.2 ContextSpec", H2))
    s.append(code(
        "ContextSpec:\n"
        "  spec_id:        string\n"
        "  task_id:        string\n"
        "  query:          string\n"
        "  generated_at:   datetime (UTC)\n"
        "  parameters:     dict\n"
        "  fragments:      list[Fragment]\n"
        "  relationship_map: list[RelationshipEdge]\n"
        "  open_questions: list[string]\n"
        "  exclusions:     list[Exclusion]\n"
        "\n"
        "Fragment:\n"
        "  source_node    node_type    node_score   fragment_score\n"
        "  depth          text         why_included"
    ))

    s.append(para("6.3 CompletionPackage", H2))
    s.append(code(
        "CompletionPackage:\n"
        "  task_id    goal    summary\n"
        "  outputs:   list[string]\n"
        "  decisions: list[Decision]\n"
        "  patterns:  list[Pattern]\n"
        "  context_usage:  high_value, low_value, missing\n"
        "  human_feedback: string\n"
        "\n"
        "Decision:  title  status  confidence  rationale\n"
        "Pattern:   title  confidence  evidence (list[string])"
    ))

    s.append(para("6.4 MemoryRecord", H2))
    s.append(code(
        "MemoryRecord:                    # in-memory projection of a vault note\n"
        "  record_id     type     title   path\n"
        "  created_at    task_id  domain  confidence\n"
        "  status:       draft | active | proposed | accepted | rejected\n"
        "              | superseded | archived\n"
        "  links         tags     human_verified\n"
        "  body          frontmatter"
    ))
    s.append(section_break())

    # ---------- 7. phases 1-9 ----------
    s.append(Paragraph("7. Implementation Phases (1 - 9)", H1))
    s.append(teal_rule())
    s.append(para(
        "All nine phases are implemented in v0.4 and covered by 150 passing tests."
    ))

    s.append(para("7.1 Phase 1 - Skeleton, schemas, config, CLI", H2))
    s.extend(bullets([
        "Pydantic v2 schemas: TaskFrame, ContextSpec, CompletionPackage, MemoryRecord.",
        "Configuration loader (cma.config.yaml) with retrieval and recorder sections.",
        "Typer-based CLI with cma init and cma version.",
        "Project scaffolding: 12 vault folders, three node folders for reasoner/retriever/recorder.",
    ]))

    s.append(para("7.2 Phase 2 - Markdown vault parser", H2))
    s.extend(bullets([
        "parse_vault, parse_note, walk_vault, extract_wikilinks.",
        "Wikilink regex strips aliases and headers: [[Note]], [[Note#Section]], [[Note|alias]] all resolve to Note.",
        "YAML frontmatter via python-frontmatter; unknown type falls back to note.",
        "MemoryRecord projection holds body, frontmatter, links, status, tags, confidence.",
    ]))

    s.append(para("7.3 Phase 3 - Graph index and health", H2))
    s.extend(bullets([
        "NetworkX DiGraph keyed by record_id; wikilinks resolve title -> stem -> placeholder.",
        "graph_health_report: total nodes, edges, orphans, broken links, type breakdown.",
        "cma graph health CLI command.",
    ]))

    s.append(para("7.4 Phase 4 - Hybrid retrieval", H2))
    s.extend(bullets([
        "BM25L (not BM25Okapi). Title repeated 3x to weight it.",
        "Pluggable Embedder protocol; SentenceTransformerEmbedder and OpenAIEmbedder built-in (lazy-imported).",
        "Hybrid score = alpha * sem + (1 - alpha) * lex; metadata boosts; depth decay.",
        "Beam-pruned BFS over outgoing AND incoming edges.",
        "Paragraph-level fragment extraction with cross-node Jaccard dedup.",
        "ContextSpec assembly + markdown rendering.",
        "cma index persists nodes.json, BM25 pickle, embedding matrix.",
        "cma retrieve \"...\" with --json, --save, --max-depth flags.",
    ]))
    s.append(para("Scoring formula", H3))
    s.append(code(
        "node_score   = alpha * semantic_score + (1 - alpha) * lexical_score\n"
        "final_score  = node_score * metadata_boost(record) * (depth_decay ** depth)\n"
        "\n"
        "defaults:  alpha=0.7   node_threshold=0.30   fragment_threshold=0.42\n"
        "           depth_decay=0.80   beam_width=5   max_depth=2\n"
        "           max_fragments_per_node=3\n"
        "\n"
        "metadata boosts:\n"
        "  accepted decision      +0.10\n"
        "  superseded decision    -0.50\n"
        "  rejected decision      -0.30\n"
        "  human_verified         +0.10\n"
        "  confidence >= 0.85     +0.08\n"
        "  confidence <  0.30     -0.10\n"
        "  status archived        -0.20"
    ))

    s.append(para("7.5 Phase 5 - Recorder", H2))
    s.extend(bullets([
        "WRITE / DRAFT / PROPOSE / SKIP routing by status + confidence (memory write policy).",
        "Markdown templates for session, decision, pattern, daily-log notes.",
        "File writers with sanitize_filename and duplicate detection.",
        "Always writes session note + appends daily-log entry.",
        "Duplicate detection by sanitized title; matching files in vault are skipped (not overwritten).",
        "JSONL audit trail at recorder/write_logs/<task_id>-write-log.jsonl.",
        "cma record <package.yaml> with --dry-run.",
    ]))
    s.append(para("Memory write policy", H3))
    s.append(code(
        "decision rules:\n"
        "  status accepted/rejected   ->  WRITE\n"
        "  status proposed\n"
        "    confidence >= 0.75       ->  WRITE\n"
        "    confidence >= 0.50       ->  DRAFT (status=draft)\n"
        "    confidence >= 0.25       ->  PROPOSE (recorder/memory_write_proposals/)\n"
        "  status superseded          ->  WRITE (or PROPOSE if configured)\n"
        "  any < 0.25                 ->  SKIP\n"
        "\n"
        "pattern rules:\n"
        "  confidence >= 0.75         ->  WRITE\n"
        "  confidence >= 0.50         ->  DRAFT (or PROPOSE if configured)\n"
        "  confidence >= 0.25         ->  PROPOSE\n"
        "  any < 0.25                 ->  SKIP"
    ))

    s.append(para("7.6 Phase 6 - MCP server", H2))
    s.extend(bullets([
        "FastMCP-based server, stdio transport.",
        "Optional install: pip install 'contextual-memory-architecture[mcp]'.",
        "cma mcp serve --project <path> launches the server.",
        "Six fine-grained graph primitives + four higher-level orchestrators (10 tools total).",
    ]))
    s.append(para("The 10 MCP tools", H3))
    s.append(make_table(
        ["Tool", "Purpose"],
        [
            ["search_notes",          "Hybrid BM25 + embedding search; returns top_k matches."],
            ["get_note",              "Fetch a note's full body, frontmatter, and links."],
            ["get_outgoing_links",    "Notes this note links to via wikilinks."],
            ["get_backlinks",         "Notes that link to this note."],
            ["traverse_graph",        "BFS within N hops of a start note."],
            ["search_by_frontmatter", "Filter notes by YAML metadata key/value."],
            ["retrieve",              "Full Retriever pipeline -> rendered markdown Context Spec."],
            ["record_completion",     "Recorder ingestion (YAML string -> vault writes)."],
            ["graph_health",          "Structural health report."],
            ["reindex",               "Rebuild in-memory Retriever/Recorder state."],
        ],
    ))
    s.append(para("Claude Code integration snippet", H3))
    s.append(code(
        '// ~/.claude/mcp.json\n'
        '{\n'
        '  "mcpServers": {\n'
        '    "cma": {\n'
        '      "command": "cma",\n'
        '      "args": ["mcp", "serve", "--project",\n'
        '               "/absolute/path/to/your/cma-project"]\n'
        '    }\n'
        '  }\n'
        '}'
    ))

    s.append(para("7.7 Phase 7 - Evaluation harness", H2))
    s.extend(bullets([
        "Recall@k, Precision@k, MRR, Memory Usefulness Score, Context Efficiency Score.",
        "Four modes: NO_MEMORY, VECTOR_ONLY, GRAPHRAG, FULL_CMA.",
        "cma evals run <bench.yaml> --mode graphrag --save out.json.",
        "Sample benchmark at examples/benchmark.yaml.",
    ]))
    s.append(para("Memory Usefulness Score (MUS)", H3))
    s.append(code(
        "MUS = +2.0 * relevant_used\n"
        "      +2.0 * prior_decision_applied\n"
        "      +2.0 * prior_failure_avoided\n"
        "      -1.0 * irrelevant_included\n"
        "      -3.0 * critical_missed\n"
        "      -2.0 * stale_or_superseded_used"
    ))

    s.append(para("7.8 Phase 8 - Memory health and observability", H2))
    s.extend(bullets([
        "health_report returns a dict with vault, indexes, graph, and retrieval sub-reports.",
        "Soft thresholds: vault > 50K notes, embeddings > 200 MB, orphan rate > 30%, broken-link rate > 5%, never-retrieved > 70%.",
        "log_retrieval appends per-event JSON to .cma/state/retrieval_log.jsonl.",
        "Retriever auto-logs every retrieve() call (best-effort).",
        "cma retrieve emits a context budget gauge: [#######-----]  1,847 / 8,000 tokens (23%).",
        "cma health [--json] CLI command with rich tables.",
    ]))

    s.append(para("7.9 Phase 9 - Memory lifecycle", H2))
    s.extend(bullets([
        "archive_note, archive_cold_notes, supersede_decision.",
        "cma archive --type pattern --older-than 90 [--dry-run].",
        "cma supersede \"Old Decision\" --by \"New Decision\".",
        "Archive moves files to vault/011-archive/, sets status=archived and archived_at.",
        "Cold-ness = (last_retrieval older than N days) OR (no log entry AND created frontmatter older than N days). No signal -> skipped.",
        "Filename collisions handled by suffix: <stem>-archived-YYYYMMDD-HHMMSS.md.",
        "Supersede updates frontmatter (status, superseded_by, superseded_at) and appends \"Superseded by [[New]].\" to the body.",
    ]))
    s.append(section_break())

    # ---------- 8. CLI reference ----------
    s.append(Paragraph("8. CLI Reference", H1))
    s.append(teal_rule())
    s.append(make_table(
        ["Command", "Description"],
        [
            ["cma init <path>",                                                        "Scaffold a new project."],
            ["cma setup [path]",                                                       "Interactive: integration + embedding provider."],
            ["cma index [path] [--no-embeddings]",                                     "Training phase: parse, build graph, BM25, embeddings."],
            ["cma graph health [path]",                                                "Graph structure report."],
            ["cma retrieve \"<query>\" [--max-depth N] [--save P] [--json]",           "Run Retriever, emit Context Spec, show context budget."],
            ["cma record <package.yaml> [--dry-run]",                                  "Recorder ingestion."],
            ["cma evals run <bench.yaml> [--mode M] [--save out.json]",                "Benchmark suite runner."],
            ["cma mcp serve [--project p]",                                            "Start MCP server over stdio."],
            ["cma health [--json]",                                                    "Memory health report."],
            ["cma archive [--type T] [--status S] [--older-than D] [--dry-run]",       "Archive cold notes."],
            ["cma supersede \"Old\" --by \"New\" [--dry-run]",                         "Mark old as superseded."],
            ["cma version",                                                            "Print installed version."],
        ],
    ))
    s.append(section_break())

    # ---------- 9. config reference ----------
    s.append(Paragraph("9. Configuration Reference", H1))
    s.append(teal_rule())
    s.append(code(
        "# cma.config.yaml\n"
        "vault_path: ./vault                # canonical memory location\n"
        "index_path: ./.cma                  # derived state location\n"
        "embedding_provider: sentence-transformers\n"
        "                                    # options: sentence-transformers | openai | none\n"
        "embedding_model: all-MiniLM-L6-v2\n"
        "\n"
        "retrieval:\n"
        "  alpha: 0.7                        # 0=lexical only, 1=semantic only\n"
        "  max_depth: 2\n"
        "  beam_width: 5\n"
        "  node_threshold: 0.30              # seed score floor (NOT applied to traversed nodes)\n"
        "  fragment_threshold: 0.42\n"
        "  depth_decay: 0.80\n"
        "  max_fragments_per_node: 3\n"
        "\n"
        "recorder:\n"
        "  require_human_approval_for:\n"
        "    - autonomy_change\n"
        "    - low_confidence_pattern\n"
        "    - supersede_decision\n"
        "  default_confidence: 0.60"
    ))
    s.append(section_break())

    # ---------- 10. ADRs ----------
    s.append(Paragraph("10. Architectural Decisions", H1))
    s.append(teal_rule())

    s.append(para("10.1 BM25L over BM25Okapi", H2))
    s.append(para(
        "Initial implementation used BM25Okapi. Its IDF formula goes to zero or negative "
        "when a term appears in more than half the documents - a degenerate case in our "
        "corpus because wikilink anchor text duplicates terms across linked notes. "
        "BM25Plus avoids the negative IDF but introduces a delta term that gives every "
        "doc a non-zero baseline, which our threshold-based filtering treated as false "
        "positives. <b>BM25L</b> uses log((N+1) / (df+0.5)) - always positive, but "
        "zero-floor for docs with no query terms. This is the right shape for graph-"
        "derived corpora."
    ))

    s.append(para("10.2 node_threshold gates seeds, not traversed nodes", H2))
    s.append(para(
        "The original whitepaper listed node_threshold as a final filter. In practice, a "
        "graph-linked pattern at depth 1 from a strong seed often scored below 0.30 "
        "because it had no direct query overlap - only the wikilink mention earned its "
        "place. Filtering it would defeat the entire point of GraphRAG. Resolution: "
        "<b>node_threshold gates seed selection only.</b> Traversed nodes earn inclusion "
        "via graph adjacency; beam_width and max_depth control volume."
    ))

    s.append(para("10.3 Title repetition for BM25", H2))
    s.append(para(
        "Tokenization concatenates the title 3x before the body. A cheap way to give "
        "title tokens a stronger BM25 signal without learning a separate field-weighted "
        "index. Plays well with BM25L's TF-saturation behavior."
    ))

    s.append(para("10.4 Vault is canonical, .cma/ is rebuildable", H2))
    s.append(para(
        "Memory must survive index corruption, version upgrades, and tool changes. "
        "Markdown with YAML frontmatter and wikilinks is the spec. Embeddings, BM25 "
        "pickles, graph JSON, and retrieval logs all live under .cma/ and can be wiped "
        "and rebuilt by cma index."
    ))

    s.append(para("10.5 Per-agent vaults; fractal-by-design", H2))
    s.append(para(
        "Default to one vault per agent - no shared global brain - so experiences "
        "don't cross-contaminate. The local-first markdown design is what makes the "
        "fractal framing tractable: a vault is a portable artifact, an MCP server is a "
        "portable interface, and a graph of vaults is just another graph."
    ))
    s.append(section_break())

    # ---------- 11. memory at scale ----------
    s.append(Paragraph("11. Memory at Scale", H1))
    s.append(teal_rule())
    s.append(para(
        "You cannot have infinite learned memory. CMA addresses this with health "
        "observability (Phase 8) and explicit curation (Phase 9). Realistic single-"
        "vault projections on a typical laptop:"
    ))
    s.append(make_table(
        ["Vault size", "Markdown", "Embeddings", "RAM", "Query latency"],
        [
            ["1K notes",   "~10 MB",  "~1.5 MB",   "~50 MB",   "<50 ms"],
            ["10K notes",  "~100 MB", "~15 MB",    "~250 MB",  "<100 ms"],
            ["100K notes", "~1 GB",   "~150 MB",   "~1.5 GB",  "~500 ms"],
            ["1M notes",   "~10 GB",  "~1.5 GB",   "~10+ GB",  "seconds; needs ANN"],
        ],
    ))
    s.append(para(
        "When a single agent's vault crosses practical thresholds, the answer is to "
        "<b>shard by domain</b> (the fractal pattern) or <b>archive cold notes</b> "
        "(Phase 9). The automation is intentionally simple in v0.4 - you decide what's "
        "cold - because auto-archival policy decisions belong to the agent's owner, "
        "not the framework."
    ))
    s.append(section_break())

    # ---------- 12. roadmap ----------
    s.append(Paragraph("12. Roadmap (Phase 10 and Beyond)", H1))
    s.append(teal_rule())
    s.extend(bullets([
        "<b>Cluster consolidation.</b> Leiden clustering on the graph; LLM-summarize each cluster; prepend the relevant cluster summary to context specs.",
        "<b>Vault sharding.</b> Auto-split by domain when a single vault crosses size thresholds; federate retrieval across shards.",
        "<b>Decay scoring.</b> Optional metadata boost that penalizes notes by age-since-last-retrieval; off by default.",
        "<b>Cross-agent retrieval - the fractal layer.</b> Each agent's vault becomes a node in a higher-order graph; selective memory federation.",
        "<b>Typed graph edges beyond wikilinks.</b> caused-by, supersedes, dependency, contradicts - first-class edge types with type-aware scoring.",
        "<b>Memory provenance enforcement.</b> Every record answers: where did it come from, when, by whom, was it human-verified, has it been superseded.",
        "<b>HTTP+SSE MCP transport.</b> For remote Claude.ai connectors and hosted agent runtimes.",
    ]))
    s.append(Paragraph(
        "<b>Deprecated.</b> None at v0.4. Whitepaper drafts v0.1 and v0.2 are superseded by this document.",
        CALLOUT,
    ))
    s.append(section_break())

    # ---------- 13. glossary ----------
    s.append(Paragraph("13. Glossary", H1))
    s.append(teal_rule())
    s.append(make_table(
        ["Term", "Definition"],
        [
            ["CMA",            "Contextual Memory Architecture."],
            ["Reasoner",       "Judgment node; frames tasks, requests context, instructs writes."],
            ["Retriever",      "Recall node; turns memory into Context Specs via hybrid + graph search."],
            ["Recorder",       "Memory formation node; turns CompletionPackages into vault writes."],
            ["Memory",         "Durable stored experience (markdown notes in the vault)."],
            ["Context",        "Temporary working set built for a specific task."],
            ["Context spec",   "Structured artifact: fragments + relationship map + scores + provenance."],
            ["Memory graph",   "Graph of notes linked by wikilinks; nodes carry frontmatter as metadata."],
            ["Vault",          "Local Obsidian-compatible markdown directory. Canonical memory store."],
            ["Training phase", "The cma index step: parse vault, build graph, BM25, embeddings."],
            ["GraphRAG",       "Retrieval that uses graph structure (not just vector similarity)."],
            ["MCP",            "Model Context Protocol. JSON-RPC interface for agents to call tools."],
            ["MUS",            "Memory Usefulness Score. Weighted retrieval-quality metric."],
            ["CES",            "Context Efficiency Score. used_fragments / included_fragments."],
        ],
    ))
    s.append(Spacer(1, 0.4 * inch))
    s.append(HRFlowable(width="35%", thickness=1.0, color=TEAL,
                        spaceBefore=8, spaceAfter=8, hAlign="CENTER"))
    s.append(Paragraph(
        "End of whitepaper. Contextual Memory Architecture, v0.4.",
        ParagraphStyle("End", parent=BODY, alignment=TA_CENTER,
                       fontName="Helvetica-Oblique", textColor=DIM),
    ))

    return s


def main() -> None:
    doc = BaseDocTemplate(
        str(OUT),
        pagesize=LETTER,
        leftMargin=inch * 0.95,
        rightMargin=inch * 0.95,
        topMargin=inch * 0.85,
        bottomMargin=inch * 0.85,
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

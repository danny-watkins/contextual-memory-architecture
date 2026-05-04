"""Generate the CMA slideshow PDF (intro deck for Claude Code users).

Run from repo root:
    python docs/build_slideshow.py

Outputs:
    docs/CMA_Slideshow_v0.4.pdf

16:9 landscape slides, lighter on technical detail than the whitepaper. The
goal is "I want to use this in my Claude Code project" - what the system is,
how it helps, and the three commands to get started.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas

OUT = Path(__file__).parent / "CMA_Slideshow_v0.4.pdf"
PAGE = landscape((11 * inch, 8.5 * inch))  # 11x8.5 landscape

# Palette
BG = colors.HexColor("#0f1126")
BG_LIGHT = colors.HexColor("#1a1d3a")
ACCENT = colors.HexColor("#6c7cff")
ACCENT_2 = colors.HexColor("#4ade80")
TEXT = colors.HexColor("#f4f6ff")
DIM = colors.HexColor("#a0a4c8")
CODE_BG = colors.HexColor("#0a0c1c")
CARD = colors.HexColor("#22264a")


def _frame(c: rl_canvas.Canvas) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, PAGE[0], PAGE[1], fill=1, stroke=0)
    # Accent stripe
    c.setFillColor(ACCENT)
    c.rect(0, PAGE[1] - 6, PAGE[0], 6, fill=1, stroke=0)
    # Footer
    c.setFillColor(DIM)
    c.setFont("Helvetica", 9)
    c.drawString(0.6 * inch, 0.4 * inch, "Contextual Memory Architecture v0.4.0")


def _slide_number(c: rl_canvas.Canvas, n: int, total: int) -> None:
    c.setFillColor(DIM)
    c.setFont("Helvetica", 9)
    c.drawRightString(PAGE[0] - 0.6 * inch, 0.4 * inch, f"{n} / {total}")


def _h1(c: rl_canvas.Canvas, text: str, y: float = 7.2 * inch) -> None:
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 36)
    c.drawString(0.8 * inch, y, text)


def _h2(c: rl_canvas.Canvas, text: str, y: float) -> None:
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(0.8 * inch, y, text)


def _bullet(c: rl_canvas.Canvas, text: str, x: float, y: float, size: int = 16) -> None:
    c.setFillColor(ACCENT_2)
    c.circle(x + 4, y + 5, 4, fill=1, stroke=0)
    c.setFillColor(TEXT)
    c.setFont("Helvetica", size)
    c.drawString(x + 18, y, text)


def _para(c: rl_canvas.Canvas, text: str, x: float, y: float,
          size: int = 14, color=TEXT, font: str = "Helvetica",
          width: float | None = None) -> float:
    """Draw multi-line text wrapped to width (in points). Returns y after last line."""
    c.setFillColor(color)
    c.setFont(font, size)
    if width is None:
        c.drawString(x, y, text)
        return y - size * 1.4
    # naive word-wrap
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = text.split()
    line = ""
    line_h = size * 1.4
    cur_y = y
    for w in words:
        candidate = (line + " " + w).strip()
        if stringWidth(candidate, font, size) <= width:
            line = candidate
        else:
            c.drawString(x, cur_y, line)
            cur_y -= line_h
            line = w
    if line:
        c.drawString(x, cur_y, line)
        cur_y -= line_h
    return cur_y


def _code_block(c: rl_canvas.Canvas, lines: list[str], x: float, y: float,
                w: float, line_h: float = 14, size: int = 11) -> float:
    h = len(lines) * line_h + 16
    c.setFillColor(CODE_BG)
    c.roundRect(x, y - h, w, h, 6, fill=1, stroke=0)
    c.setFillColor(ACCENT_2)
    c.setFont("Courier", size)
    cy = y - 16
    for line in lines:
        c.drawString(x + 14, cy, line)
        cy -= line_h
    return y - h - 8


def _card(c: rl_canvas.Canvas, title: str, body: str, x: float, y: float,
          w: float, h: float, accent=ACCENT) -> None:
    c.setFillColor(CARD)
    c.roundRect(x, y - h, w, h, 8, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(x, y - h, 4, h, fill=1, stroke=0)
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 16, y - 22, title)
    _para(c, body, x + 16, y - 44, size=11, color=DIM, width=w - 32)


# ---- slides ----


def slide_title(c: rl_canvas.Canvas) -> None:
    _frame(c)
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 56)
    c.drawString(0.8 * inch, 5.0 * inch, "Contextual")
    c.drawString(0.8 * inch, 4.2 * inch, "Memory Architecture")
    c.setFillColor(ACCENT)
    c.setFont("Helvetica", 22)
    c.drawString(0.8 * inch, 3.4 * inch, "A lightweight memory layer your agent carries with it.")
    c.setFillColor(DIM)
    c.setFont("Helvetica", 14)
    c.drawString(0.8 * inch, 2.7 * inch, "Local-first • Obsidian-compatible • Fractal-by-design")
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.8 * inch, 1.0 * inch, "v0.4.0  •  built for Claude Code & any MCP-aware agent")


def slide_problem(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "The problem")
    _h2(c, "Most AI agents are functionally stateless.", 6.4 * inch)
    y = 5.7 * inch
    items = [
        "They forget prior decisions and conventions every session.",
        "They re-learn project context on every task (and rebill you for it).",
        "They repeat the same mistakes; they don't compound experience.",
        "Standard RAG retrieves chunks, not relationships - so the most useful context (the decision linked to the project, the postmortem linked to the failure mode) gets missed.",
    ]
    for it in items:
        _bullet(c, it, 0.8 * inch, y, 14)
        y -= 0.55 * inch
    c.setFillColor(ACCENT_2)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.8 * inch, 1.2 * inch, "Agents need durable memory that compounds, not just RAG.")


def slide_solution(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "The solution: three intelligent functions")
    _h2(c, "Memory becomes context. Context shapes action. Action becomes memory.", 6.4 * inch)
    cw = 3.0 * inch
    cx_left = 0.8 * inch
    cx_mid = cx_left + cw + 0.25 * inch
    cx_right = cx_mid + cw + 0.25 * inch
    cy = 5.6 * inch
    ch = 3.4 * inch
    _card(c, "Reasoner",
          "Frames the goal. Decides what context matters. Supervises the work. Instructs the Recorder.",
          cx_left, cy, cw, ch, ACCENT)
    _card(c, "Retriever",
          "Hybrid search + graph traversal. Builds an inspectable Context Spec - the working memory artifact.",
          cx_mid, cy, cw, ch, ACCENT_2)
    _card(c, "Recorder",
          "Turns completed tasks into structured durable memory. Sessions, decisions, patterns, daily logs.",
          cx_right, cy, cw, ch, ACCENT)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 13)
    c.drawString(0.8 * inch, 1.2 * inch,
                 "The whole system is a closed learning loop. Every task starts smarter than the last.")


def slide_per_agent_fractal(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "Per-agent. Fractal-by-design.")
    _para(c,
          "Each agent in your system carries its own CMA vault - small, local, drop-in. No shared global brain by default. Two agents working in the same project don't pollute each other's memory.",
          0.8 * inch, 6.4 * inch, size=15, color=TEXT, width=9.4 * inch)
    _para(c,
          "But a vault is a graph of notes. And a graph of vaults is just another graph. The same primitives compose upward - so when you're ready, multiple agents' memory graphs can be traversed together.",
          0.8 * inch, 5.0 * inch, size=15, color=DIM, width=9.4 * inch)
    # Simple visual: small graphs aggregating into a bigger graph
    base_y = 2.6 * inch
    # Three small clusters
    for i, cx in enumerate([2.0 * inch, 4.5 * inch, 7.0 * inch]):
        c.setFillColor(CARD)
        c.circle(cx, base_y, 0.6 * inch, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(cx, base_y - 4, f"agent {i+1}")
        # Mini graph dots
        for ang_idx, dx in enumerate([-0.25, 0.25, 0.0, -0.15, 0.15]):
            c.setFillColor(ACCENT_2)
            c.circle(cx + dx * inch, base_y + 0.3 * inch + (ang_idx % 2) * 6 - 3, 3, fill=1, stroke=0)
    # Arrows up to network
    c.setStrokeColor(DIM)
    c.setLineWidth(1.5)
    for cx in [2.0 * inch, 4.5 * inch, 7.0 * inch]:
        c.line(cx, base_y + 0.65 * inch, 9.5 * inch, 3.5 * inch)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(8.7 * inch, 3.5 * inch, "network graph")
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(8.7 * inch, 3.25 * inch, "(future direction)")


def slide_vault(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "What's in the vault")
    _h2(c, "Just markdown. You can open it in Obsidian, version it with git, grep it.", 6.4 * inch)
    lines = [
        "---",
        "type: decision",
        "title: Async Capital Call Processing",
        "status: accepted",
        "confidence: 0.86",
        "tags: [capital-calls, performance, backend]",
        "---",
        "",
        "# Async Capital Call Processing",
        "",
        "We decided to move capital call processing into",
        "an async queue.",
        "",
        "Uses [[Queue Retry Pattern]].",
        "Related: [[External API Synchronous Bottleneck]]",
    ]
    _code_block(c, lines, 0.8 * inch, 5.7 * inch, 9.4 * inch, line_h=15, size=11)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.8 * inch, 1.0 * inch,
                 "YAML frontmatter → metadata.   [[Wikilinks]] → graph edges.   Folders → clusters.")


def slide_pipeline(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "How a query becomes a Context Spec")
    steps = [
        ("1. Query in", "agent calls retrieve(\"capital call performance\")"),
        ("2. Hybrid search", "BM25 + embeddings find seed notes"),
        ("3. Graph traversal", "follow wikilinks, beam-prune, depth-decay"),
        ("4. Fragment extract", "paragraph-level, dedup across notes"),
        ("5. Context Spec out", "structured markdown with provenance"),
    ]
    y = 6.0 * inch
    for label, body in steps:
        c.setFillColor(ACCENT)
        c.circle(1.0 * inch, y + 6, 14, fill=1, stroke=0)
        c.setFillColor(BG)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(1.0 * inch, y + 1, label.split(".")[0])
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1.4 * inch, y + 6, label.split(". ", 1)[1])
        c.setFillColor(DIM)
        c.setFont("Helvetica", 13)
        c.drawString(1.4 * inch, y - 12, body)
        y -= 0.85 * inch
    c.setFillColor(ACCENT_2)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.8 * inch, 1.0 * inch,
                 "Inspectable. Debuggable. Reproducible. Not a pile of chunks.")


def slide_quickstart(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "Quickstart")
    _h2(c, "Three commands, you have a working memory layer.", 6.4 * inch)
    lines = [
        "$ pip install contextual-memory-architecture[all]",
        "",
        "$ cma init my-agent",
        "  → creates the vault, node folders, default config",
        "",
        "$ cma index my-agent",
        "  → the training phase: parse vault, build graph,",
        "    BM25 index, embeddings",
        "",
        "$ cma retrieve \"capital call performance\" --project my-agent",
        "  → emits a Context Spec, shows context budget gauge",
    ]
    _code_block(c, lines, 0.8 * inch, 5.7 * inch, 9.4 * inch, line_h=18, size=12)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.8 * inch, 1.0 * inch,
                 "All your data stays local. No cloud unless you opt into OpenAI embeddings.")


def slide_claude_code(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "Wire it into Claude Code")
    _h2(c, "Add CMA as an MCP server. The agent calls memory tools mid-task.", 6.4 * inch)
    lines = [
        "// ~/.claude/mcp.json",
        "{",
        '  "mcpServers": {',
        '    "cma": {',
        '      "command": "cma",',
        '      "args": ["mcp", "serve", "--project",',
        '               "/path/to/your/cma-project"]',
        "    }",
        "  }",
        "}",
    ]
    _code_block(c, lines, 0.8 * inch, 5.7 * inch, 5.5 * inch, line_h=18, size=12)
    # Tool list panel
    panel_x = 6.6 * inch
    panel_y = 5.7 * inch
    panel_w = 3.6 * inch
    panel_h = 4.4 * inch
    c.setFillColor(CARD)
    c.roundRect(panel_x, panel_y - panel_h, panel_w, panel_h, 8, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(panel_x + 16, panel_y - 24, "10 MCP tools available:")
    tools = [
        "search_notes",
        "get_note",
        "get_outgoing_links / get_backlinks",
        "traverse_graph",
        "search_by_frontmatter",
        "retrieve  (one-shot pipeline)",
        "record_completion",
        "graph_health",
        "reindex",
    ]
    ty = panel_y - 50
    for tool in tools:
        c.setFillColor(ACCENT_2)
        c.circle(panel_x + 22, ty + 4, 3, fill=1, stroke=0)
        c.setFillColor(TEXT)
        c.setFont("Courier", 11)
        c.drawString(panel_x + 32, ty, tool)
        ty -= 22
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.8 * inch, 1.0 * inch,
                 "Six fine-grained graph tools + four orchestrators. Stdio transport.")


def slide_recorder(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "The Recorder closes the loop")
    _h2(c, "When the agent finishes a task, structured memory writes back automatically.", 6.4 * inch)
    y = 5.6 * inch
    items = [
        ("Session note", "always written - what happened, why, what got decided"),
        ("Decisions", "WRITE / DRAFT / PROPOSE / SKIP based on status + confidence"),
        ("Patterns", "high-confidence patterns get promoted; weak ones go to proposals"),
        ("Daily log", "auto-appended digest of the task"),
        ("Audit trail", "JSONL log of every recorder write decision"),
    ]
    for label, body in items:
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(0.8 * inch, y, label)
        c.setFillColor(DIM)
        c.setFont("Helvetica", 14)
        c.drawString(2.4 * inch, y, body)
        y -= 0.55 * inch
    c.setFillColor(ACCENT_2)
    c.setFont("Helvetica-Oblique", 13)
    c.drawString(0.8 * inch, 1.0 * inch,
                 "Memory write policy keeps low-confidence noise out of the vault by default.")


def slide_health(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "Memory health, observability, lifecycle")
    _h2(c, "You can't have infinite learned memory. CMA gives you the dashboards and curation tools.", 6.4 * inch)
    cw = 4.5 * inch
    ch = 1.7 * inch
    cx = 0.8 * inch
    cy = 5.6 * inch
    _card(c, "cma health",
          "Vault size, index footprint, graph density, retrieval activity. Soft warnings when you cross thresholds (>50K notes, >200MB embeddings, etc).",
          cx, cy, cw, ch, ACCENT)
    _card(c, "Context budget gauge",
          "Every retrieve shows: [#######-----] 1,847 / 8,000 tokens (23%). You see exactly how much memory you're pulling.",
          cx + cw + 0.25 * inch, cy, cw, ch, ACCENT_2)
    cy2 = cy - ch - 0.3 * inch
    _card(c, "cma archive",
          "Move cold notes to vault/011-archive/. Filter by --type, --status, --older-than. Falls back from retrieval log -> created date -> skip.",
          cx, cy2, cw, ch, ACCENT)
    _card(c, "cma supersede",
          "Mark old decisions as superseded by newer ones. Updates frontmatter + appends a wikilink so the relationship stays graph-visible.",
          cx + cw + 0.25 * inch, cy2, cw, ch, ACCENT_2)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.8 * inch, 0.95 * inch,
                 "Curation is explicit. You decide what's cold; the framework moves the bytes.")


def slide_scale(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "Scale on real hardware")
    _h2(c, "Per-vault sizing for a single agent on a typical laptop.", 6.4 * inch)
    rows = [
        ("Vault size",   "Markdown",  "Embeddings", "RAM",     "Query latency"),
        ("1K notes",     "~10 MB",    "~1.5 MB",    "~50 MB",  "<50 ms"),
        ("10K notes",    "~100 MB",   "~15 MB",     "~250 MB", "<100 ms"),
        ("100K notes",   "~1 GB",     "~150 MB",    "~1.5 GB", "~500 ms"),
        ("1M notes",     "~10 GB",    "~1.5 GB",    "~10+ GB", "needs ANN"),
    ]
    col_x = [0.8, 2.5, 4.0, 5.6, 7.2, 8.8]
    y = 5.5 * inch
    # Header
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 14)
    for cx_in, val in zip(col_x, rows[0]):
        c.drawString(cx_in * inch, y, val)
    y -= 0.45 * inch
    c.setStrokeColor(DIM)
    c.setLineWidth(0.5)
    c.line(0.8 * inch, y + 18, 10.2 * inch, y + 18)
    for row in rows[1:]:
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 14)
        for cx_in, val in zip(col_x, row):
            c.drawString(cx_in * inch, y, val)
        y -= 0.5 * inch
    c.setFillColor(ACCENT_2)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.8 * inch, 1.5 * inch,
                 "Beyond ~100K, shard by domain (the fractal pattern) or archive cold notes.")
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(0.8 * inch, 1.05 * inch,
                 "MiniLM 384d embeddings; pure-Python core; no daemons.")


def slide_get_started(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _h1(c, "Get started")
    _h2(c, "One install. Three commands. Memory that compounds.", 6.4 * inch)
    lines = [
        "$ pip install contextual-memory-architecture[all]",
        "$ cma init my-agent && cma index my-agent",
        "$ cma mcp serve --project my-agent",
    ]
    _code_block(c, lines, 0.8 * inch, 5.4 * inch, 9.4 * inch, line_h=22, size=14)
    y = 3.4 * inch
    items = [
        ("github.com/danny-watkins/contextual-memory-architecture", ACCENT),
        ("MIT licensed.  Local-first.  No cloud unless you opt in.", DIM),
        ("Built for Claude Code; works with any MCP-aware agent.", DIM),
    ]
    for text, color in items:
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(0.8 * inch, y, text)
        y -= 0.5 * inch


SLIDES = [
    slide_title,
    slide_problem,
    slide_solution,
    slide_per_agent_fractal,
    slide_vault,
    slide_pipeline,
    slide_quickstart,
    slide_claude_code,
    slide_recorder,
    slide_health,
    slide_scale,
    slide_get_started,
]


def main() -> None:
    c = rl_canvas.Canvas(str(OUT), pagesize=PAGE)
    c.setTitle("CMA - Contextual Memory Architecture")
    c.setAuthor("Danny Watkins")
    c.setSubject("Introduction to CMA for Claude Code users")
    total = len(SLIDES)
    for i, slide_fn in enumerate(SLIDES, start=1):
        slide_fn(c)
        if slide_fn is not slide_title:
            _slide_number(c, i, total)
        c.showPage()
    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

"""Generate the CMA slideshow PDF (intro deck for Claude Code users).

Matches the visual style of CMA_Whitepaper_v0.2 (teal on white, sans-serif).
Bigger type, more whitespace - it's a deck, not a doc.

Run:
    python docs/build_slideshow.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

OUT = Path(__file__).parent / "CMA_Slideshow_v0.4.pdf"
PAGE = landscape((11 * inch, 8.5 * inch))

# Same palette as whitepaper for consistency.
TEAL = colors.HexColor("#2C7884")
TEAL_LIGHT = colors.HexColor("#5da6b3")
TEAL_BG = colors.HexColor("#e8f1f3")
TEXT = colors.HexColor("#1f1f1f")
DIM = colors.HexColor("#666666")
RULE = colors.HexColor("#cfd8db")
CODE_BG = colors.HexColor("#f5f5f5")
ROW_ALT = colors.HexColor("#f4f6f7")


# ----- chrome ------


def _frame(c: rl_canvas.Canvas) -> None:
    # White background (pdf default)
    # Top teal band
    c.setFillColor(TEAL)
    c.rect(0, PAGE[1] - 0.25 * inch, PAGE[0], 0.25 * inch, fill=1, stroke=0)
    # Bottom thin teal rule
    c.setStrokeColor(TEAL)
    c.setLineWidth(2)
    c.line(0.7 * inch, 0.55 * inch, PAGE[0] - 0.7 * inch, 0.55 * inch)
    # Footer
    c.setFillColor(DIM)
    c.setFont("Helvetica", 9)
    c.drawString(0.7 * inch, 0.32 * inch,
                 "Contextual Memory Architecture (CMA) - v0.4")


def _slide_number(c: rl_canvas.Canvas, n: int, total: int) -> None:
    c.setFillColor(DIM)
    c.setFont("Helvetica", 9)
    c.drawRightString(PAGE[0] - 0.7 * inch, 0.32 * inch, f"{n} / {total}")


def _h1(c: rl_canvas.Canvas, text: str, y: float = 7.0 * inch) -> None:
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 32)
    c.drawString(0.85 * inch, y, text)
    # Underline accent
    c.setStrokeColor(TEAL)
    c.setLineWidth(2.5)
    c.line(0.85 * inch, y - 12, 0.85 * inch + 0.6 * inch, y - 12)


def _eyebrow(c: rl_canvas.Canvas, text: str, y: float) -> None:
    c.setFillColor(TEAL_LIGHT)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.85 * inch, y, text.upper())


def _subtitle(c: rl_canvas.Canvas, text: str, y: float) -> None:
    c.setFillColor(TEXT)
    c.setFont("Helvetica", 16)
    c.drawString(0.85 * inch, y, text)


def _wrap(c: rl_canvas.Canvas, text: str, x: float, y: float,
          width: float, font: str = "Helvetica", size: int = 14,
          color=TEXT, leading_factor: float = 1.45) -> float:
    c.setFillColor(color)
    c.setFont(font, size)
    words = text.split()
    line = ""
    line_h = size * leading_factor
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


def _bullet(c: rl_canvas.Canvas, text: str, x: float, y: float,
            size: int = 14, max_width: float = 8.5 * inch) -> float:
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, "—")
    return _wrap(c, text, x + 0.3 * inch, y, max_width, size=size)


def _code_block(c: rl_canvas.Canvas, lines: list[str], x: float, y: float,
                w: float, line_h: float = 16, size: int = 11) -> float:
    h = len(lines) * line_h + 24
    # Background
    c.setFillColor(CODE_BG)
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.roundRect(x, y - h, w, h, 5, fill=1, stroke=1)
    # Code text
    c.setFillColor(TEXT)
    c.setFont("Courier", size)
    cy = y - 18
    for line in lines:
        c.drawString(x + 14, cy, line)
        cy -= line_h
    return y - h - 12


def _card(c: rl_canvas.Canvas, title: str, body: str, x: float, y: float,
          w: float, h: float) -> None:
    # Subtle teal-tinted card with teal left border
    c.setFillColor(TEAL_BG)
    c.roundRect(x, y - h, w, h, 6, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(x, y - h, 4, h, fill=1, stroke=0)
    # Title
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x + 18, y - 26, title)
    # Body wrapped
    _wrap(c, body, x + 18, y - 50, w - 32, size=11.5, color=TEXT,
          leading_factor=1.45)


# ----- slides -----


def slide_title(c: rl_canvas.Canvas) -> None:
    _frame(c)
    # Vertical centering for the title slide
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 60)
    c.drawString(0.85 * inch, 5.4 * inch, "Contextual")
    c.drawString(0.85 * inch, 4.6 * inch, "Memory Architecture")
    # Accent rule
    c.setStrokeColor(TEAL)
    c.setLineWidth(3)
    c.line(0.85 * inch, 4.2 * inch, 4.5 * inch, 4.2 * inch)
    # Subtitle
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Oblique", 22)
    c.drawString(0.85 * inch, 3.5 * inch,
                 "A lightweight memory layer your agent carries with it.")
    c.setFillColor(DIM)
    c.setFont("Helvetica", 14)
    c.drawString(0.85 * inch, 2.9 * inch,
                 "Local-first  -  Obsidian-compatible  -  Fractal-by-design")
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.85 * inch, 1.0 * inch,
                 "v0.4  -  built for Claude Code and any MCP-aware agent")


def slide_problem(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "1. The problem", 7.4 * inch)
    _h1(c, "Most AI agents are stateless.", 6.8 * inch)
    y = 5.7 * inch
    items = [
        "They forget prior decisions and conventions every session.",
        "They re-learn project context on every task (and re-bill you for it).",
        "They repeat the same mistakes; they don't compound experience.",
        "Standard RAG retrieves chunks, not relationships - so the most useful context (a decision linked to a project, a postmortem linked to a failure mode) gets missed.",
    ]
    for it in items:
        y = _bullet(c, it, 0.85 * inch, y, size=15, max_width=9 * inch)
        y -= 0.18 * inch
    # Pull quote
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(0.85 * inch, 1.3 * inch,
                 "Agents need durable memory that compounds, not just RAG.")


def slide_solution(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "2. The solution", 7.4 * inch)
    _h1(c, "Three intelligent functions.", 6.8 * inch)
    _subtitle(c, "Memory becomes context. Context shapes action. Action becomes memory.",
              6.2 * inch)
    cw = 3.0 * inch
    cx_left = 0.85 * inch
    cx_mid = cx_left + cw + 0.25 * inch
    cx_right = cx_mid + cw + 0.25 * inch
    cy = 5.4 * inch
    ch = 3.2 * inch
    _card(c, "Reasoner",
          "Frames the goal. Decides what context matters. Supervises the work. Instructs the Recorder.",
          cx_left, cy, cw, ch)
    _card(c, "Retriever",
          "Hybrid search + graph traversal. Builds an inspectable Context Spec - the working memory artifact.",
          cx_mid, cy, cw, ch)
    _card(c, "Recorder",
          "Turns completed tasks into structured durable memory. Sessions, decisions, patterns, daily logs.",
          cx_right, cy, cw, ch)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 13)
    c.drawString(0.85 * inch, 1.3 * inch,
                 "A closed learning loop. Every task starts smarter than the last.")


def slide_per_agent_fractal(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "3. Architecture", 7.4 * inch)
    _h1(c, "Per-agent. Fractal-by-design.", 6.8 * inch)
    _wrap(c,
          "Each agent in your system carries its own CMA vault - small, local, drop-in. No shared global brain by default. Two agents working in the same project don't pollute each other's memory.",
          0.85 * inch, 6.0 * inch, 9.5 * inch, size=14, color=TEXT)
    _wrap(c,
          "But a vault is a graph of notes, and a graph of vaults is just another graph. The same primitives compose upward - so when you're ready, multiple agents' memory graphs can be traversed together.",
          0.85 * inch, 4.6 * inch, 9.5 * inch, size=14, color=DIM)
    # Mini diagram: 3 agent circles aggregating into a network node
    base_y = 2.5 * inch
    centers_x = [2.5 * inch, 4.5 * inch, 6.5 * inch]
    for cx in centers_x:
        c.setFillColor(TEAL_BG)
        c.setStrokeColor(TEAL)
        c.setLineWidth(1.5)
        c.circle(cx, base_y, 0.55 * inch, fill=1, stroke=1)
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(cx, base_y - 4, "vault")
        # tiny dots inside to suggest a small graph
        for dx_in in [-0.18, 0.18, 0.0]:
            c.setFillColor(TEAL)
            c.circle(cx + dx_in * inch, base_y + 0.22 * inch, 2.5, fill=1, stroke=0)
    # Arrow up to network node
    network_x = 9.0 * inch
    network_y = 3.4 * inch
    c.setStrokeColor(TEAL_LIGHT)
    c.setLineWidth(1)
    for cx in centers_x:
        c.line(cx + 0.4 * inch, base_y + 0.25 * inch, network_x - 0.5 * inch, network_y)
    c.setFillColor(TEAL)
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.5)
    c.circle(network_x, network_y, 0.5 * inch, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(network_x, network_y - 3, "network")
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(network_x, network_y - 0.8 * inch, "(future direction)")


def slide_vault(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "4. The vault", 7.4 * inch)
    _h1(c, "Just markdown.", 6.8 * inch)
    _subtitle(c, "Open it in Obsidian, version it with git, grep it from the command line.",
              6.2 * inch)
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
    _code_block(c, lines, 0.85 * inch, 5.5 * inch, 9.4 * inch, line_h=16, size=11)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.85 * inch, 1.0 * inch,
                 "YAML frontmatter -> metadata.   [[Wikilinks]] -> graph edges.   Folders -> clusters.")


def slide_pipeline(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "5. Retrieval pipeline", 7.4 * inch)
    _h1(c, "How a query becomes a Context Spec.", 6.8 * inch)
    steps = [
        ("1", "Query in",          "agent calls retrieve(\"capital call performance\")"),
        ("2", "Hybrid search",     "BM25 + embeddings find seed notes"),
        ("3", "Graph traversal",   "follow wikilinks, beam-prune, depth-decay"),
        ("4", "Fragment extract",  "paragraph-level, dedup across notes"),
        ("5", "Context Spec out",  "structured markdown with provenance"),
    ]
    y = 5.7 * inch
    for num, label, body in steps:
        # Numbered teal circle
        c.setFillColor(TEAL)
        c.circle(1.05 * inch, y + 6, 14, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(1.05 * inch, y + 1, num)
        # Label
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1.5 * inch, y + 6, label)
        # Body
        c.setFillColor(DIM)
        c.setFont("Helvetica", 13)
        c.drawString(1.5 * inch, y - 12, body)
        y -= 0.85 * inch
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.85 * inch, 1.1 * inch,
                 "Inspectable. Debuggable. Reproducible. Not a pile of chunks.")


def slide_quickstart(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "6. Quickstart", 7.4 * inch)
    _h1(c, "Three commands.", 6.8 * inch)
    _subtitle(c, "Working memory layer in under a minute.", 6.2 * inch)
    lines = [
        "$ pip install contextual-memory-architecture[all]",
        "",
        "$ cma init my-agent",
        "  -> creates the vault, node folders, default config",
        "",
        "$ cma index my-agent",
        "  -> the training phase: parse vault, build graph,",
        "     BM25 index, embeddings",
        "",
        "$ cma retrieve \"capital call performance\" --project my-agent",
        "  -> emits a Context Spec, shows context budget gauge",
    ]
    _code_block(c, lines, 0.85 * inch, 5.6 * inch, 9.4 * inch, line_h=18, size=12)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.85 * inch, 1.0 * inch,
                 "All your data stays local. No cloud unless you opt into OpenAI embeddings.")


def slide_claude_code(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "7. Claude Code integration", 7.4 * inch)
    _h1(c, "Wire it in once.", 6.8 * inch)
    _subtitle(c, "CMA exposes 10 MCP tools. The agent calls memory tools mid-task.", 6.2 * inch)
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
    _code_block(c, lines, 0.85 * inch, 5.5 * inch, 5.4 * inch, line_h=18, size=12)
    # Tool list panel (light teal)
    panel_x = 6.5 * inch
    panel_y = 5.5 * inch
    panel_w = 3.7 * inch
    panel_h = 4.3 * inch
    c.setFillColor(TEAL_BG)
    c.roundRect(panel_x, panel_y - panel_h, panel_w, panel_h, 6, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(panel_x, panel_y - panel_h, 4, panel_h, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(panel_x + 16, panel_y - 26, "Available MCP tools")
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
    ty = panel_y - 52
    for tool in tools:
        c.setFillColor(TEAL)
        c.circle(panel_x + 24, ty + 4, 2.5, fill=1, stroke=0)
        c.setFillColor(TEXT)
        c.setFont("Courier", 11)
        c.drawString(panel_x + 32, ty, tool)
        ty -= 22
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.85 * inch, 1.0 * inch,
                 "Six fine-grained graph tools and four orchestrators. Stdio transport.")


def slide_recorder(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "8. Recording back", 7.4 * inch)
    _h1(c, "The Recorder closes the loop.", 6.8 * inch)
    _subtitle(c, "When the agent finishes a task, structured memory writes back automatically.",
              6.2 * inch)
    items = [
        ("Session note",  "always written - what happened, why, what got decided"),
        ("Decisions",     "WRITE / DRAFT / PROPOSE / SKIP based on status + confidence"),
        ("Patterns",      "high-confidence patterns get promoted; weak ones go to proposals"),
        ("Daily log",     "auto-appended digest of the task"),
        ("Audit trail",   "JSONL log of every recorder write decision"),
    ]
    y = 5.4 * inch
    for label, body in items:
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(0.85 * inch, y, label)
        c.setFillColor(DIM)
        c.setFont("Helvetica", 14)
        c.drawString(2.6 * inch, y, body)
        y -= 0.6 * inch
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Oblique", 13)
    c.drawString(0.85 * inch, 1.2 * inch,
                 "Memory write policy keeps low-confidence noise out of the vault by default.")


def slide_health(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "9. Memory health and lifecycle", 7.4 * inch)
    _h1(c, "Curation, not infinity.", 6.8 * inch)
    _subtitle(c,
              "You can't have infinite learned memory. CMA gives you the dashboards and the curation tools.",
              6.2 * inch)
    cw = 4.5 * inch
    ch = 1.7 * inch
    cx_l = 0.85 * inch
    cx_r = cx_l + cw + 0.25 * inch
    cy = 5.5 * inch
    _card(c, "cma health",
          "Vault size, index footprint, graph density, retrieval activity. Soft warnings when you cross thresholds.",
          cx_l, cy, cw, ch)
    _card(c, "Context budget gauge",
          "Every retrieve shows: [#######-----]  1,847 / 8,000 tokens (23%). You see exactly how much memory you're pulling.",
          cx_r, cy, cw, ch)
    cy2 = cy - ch - 0.3 * inch
    _card(c, "cma archive",
          "Move cold notes to vault/011-archive/. Filter by --type, --status, --older-than. Falls back from retrieval log to created date to skip.",
          cx_l, cy2, cw, ch)
    _card(c, "cma supersede",
          "Mark old decisions as superseded by newer ones. Updates frontmatter and appends a wikilink so the relationship stays graph-visible.",
          cx_r, cy2, cw, ch)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0.85 * inch, 1.05 * inch,
                 "Curation is explicit. You decide what's cold; the framework moves the bytes.")


def slide_scale(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "10. Scale", 7.4 * inch)
    _h1(c, "Real numbers on real hardware.", 6.8 * inch)
    _subtitle(c, "Per-vault sizing for a single agent on a typical laptop.", 6.2 * inch)
    rows = [
        ("Vault size",   "Markdown",  "Embeddings", "RAM",     "Query latency"),
        ("1K notes",     "~10 MB",    "~1.5 MB",    "~50 MB",  "<50 ms"),
        ("10K notes",    "~100 MB",   "~15 MB",     "~250 MB", "<100 ms"),
        ("100K notes",   "~1 GB",     "~150 MB",    "~1.5 GB", "~500 ms"),
        ("1M notes",     "~10 GB",    "~1.5 GB",    "~10+ GB", "needs ANN"),
    ]
    col_x = [0.85, 2.6, 4.2, 5.9, 7.6, 9.2]
    y = 5.4 * inch
    # Header row
    c.setFillColor(TEAL)
    c.rect(0.7 * inch, y - 8, PAGE[0] - 1.4 * inch, 32, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    for cx_in, val in zip(col_x, rows[0]):
        c.drawString(cx_in * inch, y + 4, val)
    y -= 0.55 * inch
    for i, row in enumerate(rows[1:]):
        if i % 2 == 0:
            c.setFillColor(ROW_ALT)
            c.rect(0.7 * inch, y - 10, PAGE[0] - 1.4 * inch, 30, fill=1, stroke=0)
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 13)
        for cx_in, val in zip(col_x, row):
            c.drawString(cx_in * inch, y, val)
        y -= 0.55 * inch
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.85 * inch, 1.5 * inch,
                 "Beyond ~100K, shard by domain (the fractal pattern) or archive cold notes.")
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(0.85 * inch, 1.1 * inch,
                 "MiniLM 384d embeddings; pure-Python core; no daemons.")


def slide_get_started(c: rl_canvas.Canvas) -> None:
    _frame(c)
    _eyebrow(c, "11. Get started", 7.4 * inch)
    _h1(c, "One install. Three commands.", 6.8 * inch)
    _subtitle(c, "Memory that compounds.", 6.2 * inch)
    lines = [
        "$ pip install contextual-memory-architecture[all]",
        "$ cma init my-agent && cma index my-agent",
        "$ cma mcp serve --project my-agent",
    ]
    _code_block(c, lines, 0.85 * inch, 5.4 * inch, 9.4 * inch, line_h=22, size=14)
    y = 3.4 * inch
    items = [
        ("github.com/danny-watkins/contextual-memory-architecture", TEAL),
        ("MIT licensed.  Local-first.  No cloud unless you opt in.", DIM),
        ("Built for Claude Code; works with any MCP-aware agent.", DIM),
    ]
    for text, color in items:
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(0.85 * inch, y, text)
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

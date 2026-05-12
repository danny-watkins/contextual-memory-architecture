"""Generate the CMA slideshow PDF.

Audience: AI engineers and researchers (LinkedIn audit). Aesthetic: Apple
keynote / Anthropic technical reports. 16:9 widescreen, pure white, black
text, single blue accent used sparingly, Helvetica throughout, massive
typography, generous whitespace. Each slide makes ONE technically rigorous
point - no SaaS cards, no decoration that isn't functional.

Run: python docs/build_slideshow.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

OUT = Path(__file__).parent / "CMA_Slideshow_v0.5.pdf"
# 16:9 at decimal-friendly dimensions
PAGE = (13.333 * inch, 7.5 * inch)

INK = colors.HexColor("#000000")
TEXT = colors.HexColor("#1a1a1a")
DIM = colors.HexColor("#525252")
RULE = colors.HexColor("#e5e5e5")
ACCENT = colors.HexColor("#2563eb")  # confident professional blue
SOFT_BG = colors.HexColor("#f7f7f7")

MARGIN_X = 1.0 * inch
MARGIN_Y = 0.75 * inch


# ----- low-level helpers -----


def text_w(text: str, font: str, size: float) -> float:
    return stringWidth(text, font, size)


def draw_text(c, text: str, x: float, y: float, font: str = "Helvetica",
              size: float = 16, color=TEXT) -> None:
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x, y, text)


def wrap_text(c, text: str, x: float, y: float, width: float,
              font: str = "Helvetica", size: float = 16, color=TEXT,
              leading_factor: float = 1.5) -> float:
    """Word-wrap to width. Returns y-coordinate after the last line."""
    c.setFillColor(color)
    c.setFont(font, size)
    words = text.split()
    line = ""
    line_h = size * leading_factor
    cur_y = y
    for w in words:
        candidate = (line + " " + w).strip()
        if text_w(candidate, font, size) <= width:
            line = candidate
        else:
            c.drawString(x, cur_y, line)
            cur_y -= line_h
            line = w
    if line:
        c.drawString(x, cur_y, line)
        cur_y -= line_h
    return cur_y


def draw_code_lines(c, lines: list[str], x: float, y: float,
                    size: float = 13, line_h: float = 18) -> float:
    c.setFillColor(TEXT)
    c.setFont("Courier", size)
    cy = y
    for line in lines:
        c.drawString(x, cy, line)
        cy -= line_h
    return cy


def page_chrome(c, slide_num: int, total: int, label: str = "") -> None:
    """Subtle bottom-left section label and bottom-right slide number."""
    c.setFillColor(DIM)
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN_X, 0.4 * inch,
                 "Contextual Memory Architecture - v0.5 alpha")
    c.drawRightString(PAGE[0] - MARGIN_X, 0.4 * inch,
                      f"{slide_num:02d} / {total:02d}")


# ----- slide builders (each takes c, slide_num, total) -----


def slide_title(c, n, total) -> None:
    # Just title + subtitle. Maximum negative space.
    title_y = 4.7 * inch
    draw_text(c, "Contextual Memory", MARGIN_X, title_y,
              font="Helvetica-Bold", size=64, color=INK)
    draw_text(c, "Architecture.", MARGIN_X, title_y - 70,
              font="Helvetica-Bold", size=64, color=INK)
    draw_text(c, "A memory layer your agent carries with it.",
              MARGIN_X, title_y - 130, font="Helvetica", size=22, color=DIM)
    # Tiny meta block
    meta_y = 1.2 * inch
    draw_text(c, "v0.5 alpha   /   Open source (MIT)   /   github.com/danny-watkins/contextual-memory-architecture",
              MARGIN_X, meta_y, font="Helvetica", size=11, color=DIM)
    # No footer for cover
    c.setFillColor(DIM)
    c.setFont("Helvetica", 9)
    c.drawRightString(PAGE[0] - MARGIN_X, 0.4 * inch,
                      f"{n:02d} / {total:02d}")


def slide_thesis(c, n, total) -> None:
    page_chrome(c, n, total)
    # Centered single-line thesis
    title = "Memory becomes context."
    title2 = "Context shapes action."
    title3 = "Action becomes memory."
    sizes = [44, 44, 44]
    cy = 5.2 * inch
    for line, sz in zip([title, title2, title3], sizes):
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", sz)
        c.drawString(MARGIN_X, cy, line)
        cy -= sz + 14
    # Accent rule
    c.setStrokeColor(ACCENT)
    c.setLineWidth(3)
    c.line(MARGIN_X, cy + 5, MARGIN_X + 0.6 * inch, cy + 5)
    cy -= 30
    draw_text(c, "the closed loop CMA implements",
              MARGIN_X, cy, font="Helvetica-Oblique", size=16, color=DIM)


def slide_problem(c, n, total) -> None:
    page_chrome(c, n, total)
    # Big headline
    draw_text(c, "Stateless agents", MARGIN_X, 6.2 * inch,
              font="Helvetica-Bold", size=56, color=INK)
    draw_text(c, "don't compound.", MARGIN_X, 6.2 * inch - 64,
              font="Helvetica-Bold", size=56, color=INK)

    items = [
        ("They forget prior decisions every session.",                       None),
        ("They re-learn project context on every task.",                     None),
        ("They repeat mistakes; experience does not transfer.",              None),
        ("Standard RAG retrieves chunks, not relationships -",               None),
        ("    so a decision linked to the project never surfaces.",          ACCENT),
    ]
    y = 4.0 * inch
    for line, color in items:
        c.setFillColor(color or TEXT)
        c.setFont("Helvetica", 18)
        c.drawString(MARGIN_X, y, line)
        y -= 32


def slide_rag_vs_memory(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "RAG is not memory.", MARGIN_X, 6.4 * inch,
              font="Helvetica-Bold", size=44, color=INK)
    # Two columns
    col_w = (PAGE[0] - 2 * MARGIN_X - 0.6 * inch) / 2
    left_x = MARGIN_X
    right_x = MARGIN_X + col_w + 0.6 * inch
    head_y = 5.2 * inch
    # Left: standard RAG
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_x, head_y, "STANDARD RAG RETRIEVES")
    items_l = [
        "the nearest vector chunk",
        "by cosine similarity",
        "ignores edges, time, status",
        "indifferent to provenance",
    ]
    iy = head_y - 32
    for it in items_l:
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 17)
        c.drawString(left_x, iy, "—  " + it)
        iy -= 28
    # Right: agent memory
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(right_x, head_y, "AGENT MEMORY NEEDS")
    items_r = [
        "decisions linked to projects",
        "postmortems linked to failures",
        "patterns inferred across tasks",
        "supersession-aware exclusion",
    ]
    iy = head_y - 32
    for it in items_r:
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 17)
        c.drawString(right_x, iy, "—  " + it)
        iy -= 28
    # Bottom rule + note
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.line(MARGIN_X, 1.7 * inch, PAGE[0] - MARGIN_X, 1.7 * inch)
    draw_text(c, "Most useful context is structurally nearest, not semantically nearest.",
              MARGIN_X, 1.4 * inch, font="Helvetica-Oblique", size=14, color=DIM)


def slide_architecture(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Three intelligent functions.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=44, color=INK)
    # Three boxes in a row connected by arrows
    box_w = 3.0 * inch
    box_h = 1.6 * inch
    gap = 0.5 * inch
    total_w = 3 * box_w + 2 * gap
    start_x = (PAGE[0] - total_w) / 2
    cy = 4.4 * inch  # box top
    titles = ["Reasoner", "Retriever", "Recorder"]
    blurbs = [
        "frames the goal, decides what context matters",
        "memory -> context spec via hybrid + graph search",
        "experience -> structured durable memory",
    ]
    for i, (t, b) in enumerate(zip(titles, blurbs)):
        x = start_x + i * (box_w + gap)
        # Box
        c.setStrokeColor(INK)
        c.setLineWidth(1.2)
        c.rect(x, cy - box_h, box_w, box_h, fill=0, stroke=1)
        # Title
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(x + 18, cy - 36, t)
        # Body
        wrap_text(c, b, x + 18, cy - 70, box_w - 36,
                  font="Helvetica", size=13, color=DIM, leading_factor=1.4)
        # Arrow to next
        if i < 2:
            ax_start = x + box_w + 4
            ax_end = x + box_w + gap - 4
            ay = cy - box_h / 2
            c.setStrokeColor(ACCENT)
            c.setLineWidth(2)
            c.line(ax_start, ay, ax_end, ay)
            # Arrow head
            c.setFillColor(ACCENT)
            p = c.beginPath()
            p.moveTo(ax_end, ay)
            p.lineTo(ax_end - 6, ay - 4)
            p.lineTo(ax_end - 6, ay + 4)
            p.close()
            c.drawPath(p, fill=1, stroke=0)
    # Curved feedback arrow underneath (just a label)
    feedback_y = cy - box_h - 0.7 * inch
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.5)
    c.line(start_x + 0.5 * inch, feedback_y,
           start_x + total_w - 0.5 * inch, feedback_y)
    # Up arrows at ends
    for end_x in [start_x + 0.5 * inch, start_x + total_w - 0.5 * inch]:
        c.line(end_x, feedback_y, end_x, feedback_y + 0.2 * inch)
    draw_text(c, "memory feeds the next task",
              start_x + total_w / 2 - 1.3 * inch,
              feedback_y - 0.35 * inch,
              font="Helvetica-Oblique", size=13, color=DIM)


def slide_vault(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "The vault is the memory.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=44, color=INK)
    draw_text(c, "Just markdown. Open in Obsidian, version with git, grep from the shell.",
              MARGIN_X, 6.5 * inch - 38, font="Helvetica", size=15, color=DIM)
    # Code block (no fancy box, just monospace block)
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
    ]
    code_x = MARGIN_X + 0.2 * inch
    code_y = 5.4 * inch
    draw_code_lines(c, lines, code_x, code_y, size=13, line_h=18)
    # Annotations on the right
    ann_x = MARGIN_X + 6.5 * inch
    annotations = [
        ("YAML frontmatter",         "machine-readable metadata"),
        ("[[Wikilinks]]",             "graph edges between notes"),
        ("Filename",                  "stable record id"),
    ]
    ay = 5.0 * inch
    for label, body in annotations:
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(ann_x, ay, label)
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 13)
        c.drawString(ann_x, ay - 20, body)
        ay -= 60


def slide_pipeline(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "The retrieval pipeline.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=44, color=INK)
    draw_text(c, "Five deterministic stages from query to Context Spec.",
              MARGIN_X, 6.5 * inch - 38, font="Helvetica", size=15, color=DIM)
    steps = [
        ("01", "Hybrid seed search",
               "BM25L lexical  +  optional dense embeddings  =  hybrid score"),
        ("02", "Beam-pruned multi-hop traversal",
               "expand outward over wikilinks, beam-prune at each depth"),
        ("03", "Final scoring",
               "metadata boost  *  depth_decay ^ depth"),
        ("04", "Paragraph-level fragment extraction",
               "score paragraphs against query, dedupe across nodes"),
        ("05", "Context Spec assembly",
               "structured artifact: fragments + relationship map + provenance"),
    ]
    y = 5.3 * inch
    for num, label, body in steps:
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(MARGIN_X, y, num)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 19)
        c.drawString(MARGIN_X + 0.7 * inch, y, label)
        c.setFillColor(DIM)
        c.setFont("Helvetica", 14)
        c.drawString(MARGIN_X + 0.7 * inch, y - 22, body)
        y -= 0.78 * inch


def slide_scoring(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Hybrid scoring with depth decay.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=42, color=INK)
    draw_text(c, "Lexical + semantic, modulated by metadata and depth.",
              MARGIN_X, 6.5 * inch - 34, font="Helvetica", size=15, color=DIM)
    # Equations
    eq_y = 5.45 * inch
    eq_x = MARGIN_X
    c.setFillColor(INK)
    c.setFont("Helvetica", 22)
    c.drawString(eq_x, eq_y,
                 "node_score   =   alpha . semantic   +   (1 - alpha) . lexical")
    c.drawString(eq_x, eq_y - 44,
                 "final_score  =   node_score  *  metadata_boost  *  decay ^ depth")
    # Defaults block (left)
    box_y = 3.8 * inch
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    box_x = MARGIN_X
    box_w = 4.6 * inch
    box_h = 1.8 * inch
    c.rect(box_x, box_y - box_h, box_w, box_h, fill=0, stroke=1)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(box_x + 14, box_y - 22, "DEFAULTS")
    defaults = [
        "alpha = 0.7              decay = 0.80",
        "node_threshold = 0.30    beam_width = 5",
        "fragment_threshold = 0.42  max_depth = 2",
    ]
    dy = box_y - 46
    for d in defaults:
        c.setFillColor(TEXT)
        c.setFont("Courier", 13)
        c.drawString(box_x + 14, dy, d)
        dy -= 20
    # Boost table (right) -- multipliers, clamped at 0
    btx = MARGIN_X + 5.0 * inch
    bty = 3.8 * inch
    btw = 5.5 * inch
    bth = 2.55 * inch
    c.rect(btx, bty - bth, btw, bth, fill=0, stroke=1)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(btx + 14, bty - 22, "METADATA BOOSTS  (multiplicative, clamped at 0)")
    rows = [
        ("accepted decision",      "x 1.10"),
        ("rejected decision",      "x 0.70"),
        ("superseded decision",    "x 0.50"),
        ("archived (any type)",    "x 0.80"),
        ("human_verified",         "x 1.10"),
        ("confidence >= 0.85",     "x 1.08"),
        ("confidence <  0.30",     "x 0.90"),
    ]
    ry = bty - 46
    for label, val in rows:
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 12)
        c.drawString(btx + 14, ry, label)
        c.setFillColor(ACCENT)
        c.setFont("Courier-Bold", 12)
        c.drawRightString(btx + btw - 14, ry, val)
        ry -= 18
    # Footer notes (two lines)
    draw_text(c, "If either modality is 0 (e.g. embedder disabled), the score falls back to whichever is non-zero. No missing-modality penalty.",
              MARGIN_X, 1.45 * inch, font="Helvetica-Oblique", size=11, color=DIM)
    draw_text(c, "node_threshold gates SEEDS only - traversed nodes earn inclusion via graph adjacency.",
              MARGIN_X, 1.15 * inch, font="Helvetica-Oblique", size=11, color=DIM)


def slide_traversal(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Beam-pruned multi-hop.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=44, color=INK)
    draw_text(c, "BFS over outgoing AND incoming edges, pruned by inherited score.",
              MARGIN_X, 6.5 * inch - 38, font="Helvetica", size=15, color=DIM)
    # Diagram on left: simple graph showing depths 0/1/2 with beam
    diag_x = MARGIN_X + 0.3 * inch
    cx0, cy0 = diag_x + 0.5 * inch, 4.0 * inch
    # Depth 0 (seed)
    c.setStrokeColor(ACCENT)
    c.setFillColor(ACCENT)
    c.setLineWidth(1.5)
    c.circle(cx0, cy0, 14, fill=1, stroke=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(cx0, cy0 - 4, "S")
    c.setFillColor(DIM)
    c.setFont("Helvetica", 10)
    c.drawCentredString(cx0, cy0 - 28, "depth 0")
    # Depth 1: 3 nodes (beam_width subset of all neighbors)
    d1_x = diag_x + 1.7 * inch
    d1_ys = [cy0 + 0.7 * inch, cy0, cy0 - 0.7 * inch]
    for y in d1_ys:
        c.setStrokeColor(INK)
        c.setLineWidth(0.5)
        c.line(cx0 + 14, cy0, d1_x - 14, y)
        c.setFillColor(colors.white)
        c.setStrokeColor(INK)
        c.setLineWidth(1)
        c.circle(d1_x, y, 12, fill=1, stroke=1)
    c.setFillColor(DIM)
    c.setFont("Helvetica", 10)
    c.drawCentredString(d1_x, cy0 - 1.05 * inch, "depth 1")
    # Depth 2: 2 nodes (beam-pruned further)
    d2_x = diag_x + 3.0 * inch
    d2_ys = [cy0 + 0.4 * inch, cy0 - 0.4 * inch]
    for y in d2_ys:
        c.setStrokeColor(INK)
        c.setLineWidth(0.5)
        c.line(d1_x + 12, d1_ys[1], d2_x - 12, y)
        c.setFillColor(SOFT_BG)
        c.setStrokeColor(DIM)
        c.setLineWidth(1)
        c.circle(d2_x, y, 11, fill=1, stroke=1)
    c.setFillColor(DIM)
    c.setFont("Helvetica", 10)
    c.drawCentredString(d2_x, cy0 - 1.05 * inch, "depth 2")
    # Pseudocode on right
    code_x = MARGIN_X + 4.6 * inch
    code_y = 5.5 * inch
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(code_x, code_y, "ALGORITHM")
    code_lines = [
        "frontier <- seeds_above_threshold(query)",
        "for d in 1..max_depth:",
        "    candidates <- {}",
        "    for n in frontier:",
        "        for m in neighbors(n):     # forward + backward",
        "            if m not visited and exists(m):",
        "                inherit parent score",
        "    keep top-beam_width by inherited score",
        "    visit them at depth d",
        "    frontier <- ranked",
    ]
    cy = code_y - 22
    for line in code_lines:
        c.setFillColor(TEXT)
        c.setFont("Courier", 11)
        c.drawString(code_x, cy, line)
        cy -= 16


def slide_recorder(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Memory write policy.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=44, color=INK)
    draw_text(c, "Confidence-gated routing keeps low-signal noise out of the vault.",
              MARGIN_X, 6.5 * inch - 38, font="Helvetica", size=15, color=DIM)
    # Table: confidence band x action
    rows = [
        ["status",       "confidence",      "action",     "destination"],
        ["accepted",     "any",             "WRITE",      "vault/003-decisions/"],
        ["rejected",     "any",             "WRITE",      "vault/003-decisions/"],
        ["proposed",     ">= 0.75",         "WRITE",      "vault/003-decisions/"],
        ["proposed",     "0.50 - 0.74",     "DRAFT",      "vault/003-decisions/  (status=draft)"],
        ["proposed",     "0.25 - 0.49",     "PROPOSE",    "recorder/memory_write_proposals/"],
        ["any",          "< 0.25",          "SKIP",       "—"],
    ]
    col_x = [MARGIN_X, MARGIN_X + 1.4 * inch, MARGIN_X + 3.1 * inch, MARGIN_X + 4.8 * inch]
    col_w = [1.4 * inch, 1.7 * inch, 1.7 * inch, 5.5 * inch]
    y = 5.3 * inch
    # Header
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.line(MARGIN_X, y + 4, PAGE[0] - MARGIN_X, y + 4)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 12)
    for x, h in zip(col_x, rows[0]):
        c.drawString(x, y - 16, h.upper())
    c.line(MARGIN_X, y - 24, PAGE[0] - MARGIN_X, y - 24)
    y -= 50
    # Rows
    for i, row in enumerate(rows[1:]):
        if i % 2 == 0:
            c.setFillColor(SOFT_BG)
            c.rect(MARGIN_X - 4, y - 14, PAGE[0] - 2 * MARGIN_X + 8, 26, fill=1, stroke=0)
        action = row[2]
        for x, val in zip(col_x, row):
            if val == action and val in ("WRITE", "DRAFT", "PROPOSE", "SKIP"):
                c.setFillColor(ACCENT)
                c.setFont("Courier-Bold", 12)
            else:
                c.setFillColor(TEXT)
                c.setFont("Helvetica", 13)
            c.drawString(x, y, val)
        y -= 32


def slide_mcp_tools(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Ten MCP tools for any agent.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=42, color=INK)
    draw_text(c, "Six fine-grained graph primitives + four orchestrators. Stdio transport.",
              MARGIN_X, 6.5 * inch - 38, font="Helvetica", size=15, color=DIM)
    # Two columns of tool signatures
    col_w = (PAGE[0] - 2 * MARGIN_X - 0.6 * inch) / 2
    left_x = MARGIN_X
    right_x = MARGIN_X + col_w + 0.6 * inch
    # Left: graph primitives
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_x, 5.3 * inch, "GRAPH PRIMITIVES")
    primitives = [
        ("search_notes",          "(query, top_k)"),
        ("get_note",              "(title)"),
        ("get_outgoing_links",    "(title)"),
        ("get_backlinks",         "(title)"),
        ("traverse_graph",        "(start, depth)"),
        ("search_by_frontmatter", "(key, value)"),
    ]
    py = 5.0 * inch
    for name, sig in primitives:
        c.setFillColor(INK)
        c.setFont("Courier-Bold", 14)
        c.drawString(left_x, py, name)
        c.setFillColor(DIM)
        c.setFont("Courier", 13)
        c.drawString(left_x + text_w(name, "Courier-Bold", 14) + 6, py, sig)
        py -= 30
    # Right: orchestrators
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(right_x, 5.3 * inch, "ORCHESTRATORS")
    orchestrators = [
        ("retrieve",          "(query, max_depth, beam_width)"),
        ("record_completion", "(yaml, dry_run)"),
        ("graph_health",      "()"),
        ("reindex",           "()"),
    ]
    py = 5.0 * inch
    for name, sig in orchestrators:
        c.setFillColor(ACCENT)
        c.setFont("Courier-Bold", 14)
        c.drawString(right_x, py, name)
        c.setFillColor(DIM)
        c.setFont("Courier", 13)
        c.drawString(right_x + text_w(name, "Courier-Bold", 14) + 6, py, sig)
        py -= 30
    # Bottom: integration snippet
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.line(MARGIN_X, 1.9 * inch, PAGE[0] - MARGIN_X, 1.9 * inch)
    draw_text(c, "Wire into Claude Code:",
              MARGIN_X, 1.65 * inch, font="Helvetica-Bold", size=12, color=DIM)
    c.setFillColor(TEXT)
    c.setFont("Courier", 12)
    c.drawString(MARGIN_X, 1.4 * inch,
                 '{ "mcpServers": { "cma": { "command": "cma", "args": ["mcp", "serve", "--project", "..."] } } }')


def slide_fractal(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Per-agent. Fractal-by-design.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=42, color=INK)
    draw_text(c, "Each agent owns its vault. A graph of vaults is just another graph.",
              MARGIN_X, 6.5 * inch - 38, font="Helvetica", size=15, color=DIM)
    # Bottom row: 3 vault circles
    vault_y = 2.6 * inch
    centers_x = [MARGIN_X + 1.5 * inch, PAGE[0] / 2, PAGE[0] - MARGIN_X - 1.5 * inch]
    for cx in centers_x:
        # Vault circle
        c.setStrokeColor(INK)
        c.setLineWidth(1.2)
        c.setFillColor(colors.white)
        c.circle(cx, vault_y, 38, fill=1, stroke=1)
        # Mini graph dots inside
        for dx in [-12, 0, 12]:
            for dy in [-6, 6]:
                c.setFillColor(TEXT)
                c.circle(cx + dx, vault_y + dy, 2, fill=1, stroke=0)
        # Lines between dots
        c.setStrokeColor(DIM)
        c.setLineWidth(0.4)
        c.line(cx - 12, vault_y - 6, cx, vault_y + 6)
        c.line(cx, vault_y - 6, cx + 12, vault_y + 6)
        # Label
        c.setFillColor(DIM)
        c.setFont("Helvetica", 11)
        c.drawCentredString(cx, vault_y - 60, "agent vault")
    # Top: network graph
    net_y = 5.0 * inch
    net_x = PAGE[0] / 2
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.5)
    c.setFillColor(colors.white)
    c.circle(net_x, net_y, 50, fill=1, stroke=1)
    # Inner dots representing connected vaults
    inner_pts = [(net_x - 18, net_y + 10), (net_x + 18, net_y + 10), (net_x, net_y - 14)]
    for px, py in inner_pts:
        c.setFillColor(ACCENT)
        c.circle(px, py, 4, fill=1, stroke=0)
    # Edges between inner pts
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.8)
    for i in range(3):
        a = inner_pts[i]
        b = inner_pts[(i + 1) % 3]
        c.line(a[0], a[1], b[0], b[1])
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(net_x, net_y + 70, "NETWORK GRAPH")
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 11)
    c.drawCentredString(net_x, net_y + 55, "(future direction)")
    # Lines from each vault up to network
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    for cx in centers_x:
        c.line(cx, vault_y + 38, net_x, net_y - 50)
    # Caption bottom
    draw_text(c, "Same primitives compose upward. No central brain.",
              MARGIN_X, 1.0 * inch, font="Helvetica-Oblique", size=14, color=DIM)


def slide_health(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Memory has weight. Watch it.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=42, color=INK)
    draw_text(c, "Health observability + lifecycle curation. Memory is curated, not infinite.",
              MARGIN_X, 6.5 * inch - 38, font="Helvetica", size=15, color=DIM)
    # Top: context budget gauge mockup
    gauge_y = 5.2 * inch
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, gauge_y, "EVERY RETRIEVE EMITS")
    # Gauge bar
    bar_x = MARGIN_X
    bar_y = gauge_y - 35
    bar_w = 7.0 * inch
    bar_h = 26
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    c.rect(bar_x, bar_y, bar_w, bar_h, fill=0, stroke=1)
    fill_w = bar_w * 0.23
    c.setFillColor(ACCENT)
    c.rect(bar_x, bar_y, fill_w, bar_h, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Courier", 13)
    c.drawString(bar_x + bar_w + 14, bar_y + 7, "1,847 / 8,000 tokens  (23%)")
    # Caption
    draw_text(c, "context budget gauge - real-time, per-call",
              bar_x, bar_y - 22, font="Helvetica-Oblique", size=11, color=DIM)
    # Bottom: cma health output preview
    c.setStrokeColor(RULE)
    c.setLineWidth(0.4)
    c.line(MARGIN_X, 3.7 * inch, PAGE[0] - MARGIN_X, 3.7 * inch)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_X, 3.4 * inch, "CMA HEALTH REPORT")
    rep_lines = [
        "Vault         48 notes,  3.2 MB  (12 decisions, 22 patterns, 14 sessions)",
        "Indexes       graph 12KB  +  bm25 41KB  +  embeddings 73KB  =  126 KB",
        "Graph         107 edges,  avg out-degree 2.23,  orphan rate 4.2%",
        "Retrieval     312 events,  last 7d: 41,  most retrieved: Async Capital Call (18)",
        "Warnings      —  all metrics within healthy thresholds",
    ]
    ry = 3.05 * inch
    for line in rep_lines:
        c.setFillColor(TEXT)
        c.setFont("Courier", 12)
        c.drawString(MARGIN_X, ry, line)
        ry -= 22
    # Footer note
    draw_text(c, "cma archive  +  cma supersede  =  explicit curation, never silent decay.",
              MARGIN_X, 1.0 * inch, font="Helvetica-Oblique", size=13, color=DIM)


def slide_scaling(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Designed for single-CPU scale.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=44, color=INK)
    draw_text(c, "Projected footprint and latency on commodity hardware (MiniLM-L6-v2 384d).",
              MARGIN_X, 6.5 * inch - 38, font="Helvetica", size=15, color=DIM)
    # Table
    headers = ["Vault size", "Markdown", "Embeddings", "RAM",     "Projected latency"]
    rows = [
        ["1K notes",     "~10 MB",    "~1.5 MB",    "~50 MB",  "<50 ms"],
        ["10K notes",    "~100 MB",   "~15 MB",     "~250 MB", "<100 ms"],
        ["100K notes",   "~1 GB",     "~150 MB",    "~1.5 GB", "~500 ms"],
        ["1M notes",     "~10 GB",    "~1.5 GB",    "~10+ GB", "needs ANN"],
    ]
    col_x = [MARGIN_X, MARGIN_X + 2.0 * inch, MARGIN_X + 4.2 * inch,
             MARGIN_X + 6.4 * inch, MARGIN_X + 8.4 * inch]
    y = 5.3 * inch
    # Header
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    c.line(MARGIN_X, y + 6, PAGE[0] - MARGIN_X, y + 6)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 12)
    for x, h in zip(col_x, headers):
        c.drawString(x, y - 16, h.upper())
    c.line(MARGIN_X, y - 26, PAGE[0] - MARGIN_X, y - 26)
    y -= 56
    for i, row in enumerate(rows):
        if i % 2 == 0:
            c.setFillColor(SOFT_BG)
            c.rect(MARGIN_X - 4, y - 14, PAGE[0] - 2 * MARGIN_X + 8, 30, fill=1, stroke=0)
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 14)
        for x, val in zip(col_x, row):
            c.drawString(x, y, val)
        y -= 38
    # Bottom commentary
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.line(MARGIN_X, 1.7 * inch, PAGE[0] - MARGIN_X, 1.7 * inch)
    draw_text(c, "Projections from algorithmic complexity. Reference implementation validated on small demo vaults.",
              MARGIN_X, 1.55 * inch, font="Helvetica-Oblique", size=12, color=DIM)
    draw_text(c, "Beyond ~100K, swap to ANN structures (FAISS, hnswlib).  Beyond ~500K, shard by domain.",
              MARGIN_X, 1.25 * inch, font="Helvetica-Oblique", size=12, color=DIM)


def slide_what_its_not(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "What CMA is not.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=44, color=INK)
    items = [
        ("NOT a vector database.",
         "Embeddings are an implementation detail. The substrate is markdown."),
        ("NOT a shared global brain.",
         "Per-agent vaults by default. Cross-agent retrieval is opt-in (Phase 10+)."),
        ("NOT replacing your LLM or agent framework.",
         "It is a memory layer that drops in. CLI, Python SDK, MCP."),
        ("NOT magic auto-curation.",
         "Memory is curated explicitly. The framework moves bytes; you decide what's cold."),
    ]
    y = 5.3 * inch
    for label, body in items:
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(MARGIN_X, y, label)
        c.setFillColor(DIM)
        c.setFont("Helvetica", 15)
        c.drawString(MARGIN_X + 0.3 * inch, y - 26, body)
        y -= 0.95 * inch


def slide_get_started(c, n, total) -> None:
    page_chrome(c, n, total)
    draw_text(c, "Get started.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=56, color=INK)
    # Code block: clean, no decoration
    code_y = 5.2 * inch
    code_lines = [
        "$ git clone github.com/danny-watkins/contextual-memory-architecture",
        "$ cd contextual-memory-architecture",
        "$ pip install -e \".[all]\"",
        "",
        "$ cd /path/to/your-agent-project",
        "$ cma add        # one-shot: scaffold + ingest + wire hooks + MCP",
    ]
    cy = code_y
    for line in code_lines:
        c.setFillColor(TEXT)
        c.setFont("Courier", 18)
        c.drawString(MARGIN_X, cy, line)
        cy -= 28
    # Bottom block
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.line(MARGIN_X, 2.5 * inch, PAGE[0] - MARGIN_X, 2.5 * inch)
    draw_text(c, "github.com/danny-watkins/contextual-memory-architecture",
              MARGIN_X, 2.0 * inch, font="Helvetica-Bold", size=22, color=ACCENT)
    draw_text(c, "MIT licensed.  Local-first.  Built for Claude Code; works with any MCP-aware agent.",
              MARGIN_X, 1.5 * inch, font="Helvetica", size=14, color=DIM)


def slide_smarter_fewer_tokens(c, n, total) -> None:
    """The dual-purpose value slide: learned memory + token economy.

    Numbers are real measurements from one retrieve on the email-checker demo
    project (10 sources cited for the query "what does notify.py do"). Logged in
    cma/memory_log/activity.jsonl; per-source breakdown matches the dashboard
    screenshots referenced in SESSION_LOG.md.
    """
    page_chrome(c, n, total)
    draw_text(c, "Smarter agents, fewer tokens.", MARGIN_X, 6.5 * inch,
              font="Helvetica-Bold", size=42, color=INK)
    draw_text(c, "Same mechanism does both: cherry-pick fragments, persist what was learned.",
              MARGIN_X, 6.5 * inch - 34, font="Helvetica", size=15, color=DIM)

    # Two-point lead-in
    point_y = 5.3 * inch
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN_X, point_y, "->  MEMORY COMPOUNDS")
    c.setFillColor(DIM)
    c.setFont("Helvetica", 13)
    c.drawString(MARGIN_X + 0.3 * inch, point_y - 22,
                 "Decisions, patterns, and postmortems from prior sessions surface")
    c.drawString(MARGIN_X + 0.3 * inch, point_y - 40,
                 "automatically on the next relevant task. The agent inherits its own work.")

    point_y -= 78
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN_X, point_y, "->  CONTEXT IS CHERRY-PICKED")
    c.setFillColor(DIM)
    c.setFont("Helvetica", 13)
    c.drawString(MARGIN_X + 0.3 * inch, point_y - 22,
                 "Fragment-level extraction, not whole-document dumping. The Retriever")
    c.drawString(MARGIN_X + 0.3 * inch, point_y - 40,
                 "ranks paragraphs against the query and pulls only what's relevant.")

    # Measurement box -- left half
    box_y = 2.95 * inch
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    bx = MARGIN_X
    bw = 5.3 * inch
    bh = 1.7 * inch
    c.rect(bx, box_y - bh, bw, bh, fill=0, stroke=1)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(bx + 14, box_y - 22, "DEMO MEASUREMENT")
    c.setFillColor(DIM)
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(bx + 14, box_y - 38, "email-checker, one retrieve, 10 sources cited")
    # Numbers
    nums = [
        ("Source bodies (total)",        "2,697 tokens"),
        ("Fragments extracted",          "1,038 tokens"),
        ("Reduction",                    "61.5 %"),
    ]
    ny = box_y - 64
    for label, val in nums:
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 13)
        c.drawString(bx + 14, ny, label)
        c.setFillColor(ACCENT)
        c.setFont("Courier-Bold", 14)
        c.drawRightString(bx + bw - 14, ny, val)
        ny -= 22

    # Architectural bound box -- right half
    rbx = MARGIN_X + 5.7 * inch
    rby = 2.95 * inch
    rbw = 4.8 * inch
    rbh = 1.7 * inch
    c.rect(rbx, rby - rbh, rbw, rbh, fill=0, stroke=1)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(rbx + 14, rby - 22, "ARCHITECTURAL BOUND")
    c.setFillColor(TEXT)
    c.setFont("Helvetica", 12)
    lines = [
        "Output size is bounded by configuration",
        "(beam_width, max_depth, max_fragments_per_node),",
        "not by vault size. Cost per query stays flat",
        "as memory grows.",
    ]
    ly = rby - 46
    for line in lines:
        c.drawString(rbx + 14, ly, line)
        ly -= 18

    # Footer note
    draw_text(c, "Measurement from cma/memory_log/activity.jsonl on the email-checker demo.  Your mileage will vary with vault and query.",
              MARGIN_X, 0.95 * inch, font="Helvetica-Oblique", size=10, color=DIM)


SLIDES = [
    slide_title,
    slide_thesis,
    slide_problem,
    slide_rag_vs_memory,
    slide_architecture,
    slide_vault,
    slide_pipeline,
    slide_scoring,
    slide_traversal,
    slide_recorder,
    slide_mcp_tools,
    slide_fractal,
    slide_health,
    slide_scaling,
    slide_what_its_not,
    slide_smarter_fewer_tokens,
    slide_get_started,
]


def main() -> None:
    c = rl_canvas.Canvas(str(OUT), pagesize=PAGE)
    c.setTitle("Contextual Memory Architecture")
    c.setAuthor("Danny Watkins")
    c.setSubject("CMA - a memory layer your agent carries with it")
    total = len(SLIDES)
    for i, fn in enumerate(SLIDES, start=1):
        fn(c, i, total)
        c.showPage()
    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

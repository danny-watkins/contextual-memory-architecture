"""Generate the CMA technical whitepaper PDF.

Aesthetic reference: arxiv ML papers (Lewis et al. 2020 "Retrieval-Augmented
Generation"; Edge et al. "GraphRAG"; Anthropic technical reports). Single
column, Times-Roman body, dense prose, numbered hierarchy, Algorithm boxes,
Figure captions, justified text, tight margins.

Run: python docs/build_whitepaper.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
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

OUT = Path(__file__).parent / "CMA_Whitepaper_v0.5.pdf"
VERSION = "0.5"
TITLE = "Contextual Memory Architecture"
SUBTITLE = (
    "A Lightweight, Local-First Memory Layer for Persistent AI Agents"
)
TODAY = date.today().isoformat()

# ---- palette: subdued, paper-like ----
INK = colors.HexColor("#0a0a0a")
GRAY = colors.HexColor("#3a3a3a")
DIM = colors.HexColor("#6a6a6a")
RULE = colors.HexColor("#cfcfcf")
ACCENT = colors.HexColor("#1a3a6e")  # deep navy used sparingly
ALG_BG = colors.HexColor("#fafafa")

ss = getSampleStyleSheet()

# ---- styles: tight academic layout ----
T_TITLE = ParagraphStyle(
    "TTitle", parent=ss["Title"], fontName="Times-Bold",
    fontSize=22, leading=26, alignment=TA_CENTER, spaceAfter=4,
    textColor=INK,
)
T_SUB = ParagraphStyle(
    "TSub", parent=ss["Normal"], fontName="Times-Italic",
    fontSize=13, leading=17, alignment=TA_CENTER, spaceAfter=18,
    textColor=GRAY,
)
T_AUTHOR = ParagraphStyle(
    "TAuthor", parent=ss["Normal"], fontName="Times-Roman",
    fontSize=11, leading=14, alignment=TA_CENTER, spaceAfter=2,
    textColor=INK,
)
T_AFFIL = ParagraphStyle(
    "TAffil", parent=ss["Normal"], fontName="Times-Italic",
    fontSize=10, leading=13, alignment=TA_CENTER, spaceAfter=14,
    textColor=DIM,
)
T_DATE = ParagraphStyle(
    "TDate", parent=ss["Normal"], fontName="Times-Roman",
    fontSize=10, leading=13, alignment=TA_CENTER, spaceAfter=18,
    textColor=DIM,
)
ABSTRACT_HEAD = ParagraphStyle(
    "AbHead", parent=ss["Heading2"], fontName="Helvetica-Bold",
    fontSize=10, leading=12, alignment=TA_CENTER, spaceBefore=4,
    spaceAfter=6, textColor=INK,
)
ABSTRACT_BODY = ParagraphStyle(
    "AbBody", parent=ss["Normal"], fontName="Times-Roman",
    fontSize=10, leading=14, alignment=TA_JUSTIFY,
    leftIndent=42, rightIndent=42, spaceAfter=12, textColor=INK,
)

H1 = ParagraphStyle(
    "H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
    fontSize=12, leading=15, spaceBefore=14, spaceAfter=5,
    textColor=INK,
)
H2 = ParagraphStyle(
    "H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
    fontSize=10.5, leading=13, spaceBefore=10, spaceAfter=3,
    textColor=INK,
)
H3 = ParagraphStyle(
    "H3", parent=ss["Heading3"], fontName="Times-BoldItalic",
    fontSize=10.5, leading=13, spaceBefore=8, spaceAfter=2,
    textColor=INK,
)

BODY = ParagraphStyle(
    "Body", parent=ss["Normal"], fontName="Times-Roman",
    fontSize=10.5, leading=14, alignment=TA_JUSTIFY,
    spaceAfter=6, textColor=INK,
)
BODY_INDENT = ParagraphStyle(
    "BodyI", parent=BODY, firstLineIndent=14,
)
BULLET = ParagraphStyle(
    "Bullet", parent=BODY, leftIndent=22, bulletIndent=10,
    spaceAfter=2, alignment=TA_LEFT,
)
EQUATION = ParagraphStyle(
    "Eq", parent=ss["Normal"], fontName="Times-Italic",
    fontSize=11, leading=16, alignment=TA_CENTER,
    spaceBefore=6, spaceAfter=8, textColor=INK,
)
ALGO_HEAD = ParagraphStyle(
    "AlgHead", parent=ss["Normal"], fontName="Helvetica-Bold",
    fontSize=10, leading=13, alignment=TA_LEFT, spaceBefore=10,
    spaceAfter=2, textColor=INK,
)
ALGO_BODY = ParagraphStyle(
    "AlgBody", parent=ss["Code"], fontName="Courier",
    fontSize=8.5, leading=11.5, textColor=INK,
    leftIndent=4, rightIndent=4, spaceAfter=8, spaceBefore=2,
    backColor=ALG_BG, borderColor=RULE, borderWidth=0.4,
    borderPadding=8,
)
FIG_CAPTION = ParagraphStyle(
    "Fig", parent=ss["Normal"], fontName="Times-Roman",
    fontSize=9, leading=12, alignment=TA_CENTER, spaceBefore=4,
    spaceAfter=14, textColor=GRAY,
)
TBL_CAPTION = ParagraphStyle(
    "Tbl", parent=ss["Normal"], fontName="Times-Roman",
    fontSize=9, leading=12, alignment=TA_LEFT, spaceBefore=2,
    spaceAfter=12, textColor=GRAY,
)


def _on_page(canvas, doc):
    canvas.saveState()
    # Tiny running head
    canvas.setFont("Times-Italic", 8.5)
    canvas.setFillColor(DIM)
    canvas.drawString(inch * 0.85, LETTER[1] - inch * 0.45,
                      "Contextual Memory Architecture")
    canvas.drawRightString(LETTER[0] - inch * 0.85, LETTER[1] - inch * 0.45,
                           f"Version {VERSION}")
    # Page number
    canvas.setFont("Times-Roman", 9.5)
    canvas.setFillColor(INK)
    canvas.drawCentredString(LETTER[0] / 2, inch * 0.45, str(doc.page))
    canvas.restoreState()


def _on_first_page(canvas, doc):
    canvas.saveState()
    # Just a page number; clean cover
    canvas.setFont("Times-Roman", 9.5)
    canvas.setFillColor(INK)
    canvas.drawCentredString(LETTER[0] / 2, inch * 0.45, str(doc.page))
    canvas.restoreState()


def code(text: str, style: ParagraphStyle = ALGO_BODY) -> Preformatted:
    return Preformatted(text.strip("\n"), style)


def para(text: str, style=BODY) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: list[str]) -> list:
    return [Paragraph(f"&bull;&nbsp;&nbsp; {t}", BULLET) for t in items]


def section_break() -> PageBreak:
    return PageBreak()


def hrule() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.4, color=RULE,
                      spaceBefore=2, spaceAfter=8)


def algo(title: str, body: str) -> list:
    return [Paragraph(title, ALGO_HEAD), code(body)]


def figure_box(content_lines: list[str], caption: str) -> list:
    """ASCII-art figure with caption below."""
    body = "\n".join(content_lines)
    fig = Preformatted(body, ParagraphStyle(
        "FigBody", parent=ss["Code"], fontName="Courier",
        fontSize=8, leading=10.5, textColor=INK,
        alignment=TA_CENTER, leftIndent=24, rightIndent=24,
        spaceBefore=4, spaceAfter=2,
    ))
    return [fig, Paragraph(caption, FIG_CAPTION)]


def make_table(headers: list[str], rows: list[list[str]],
               col_widths: list[float] | None = None,
               caption: str | None = None) -> list:
    data = [headers] + rows
    t = Table(data, hAlign="LEFT", colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("TEXTCOLOR", (0, 0), (-1, 0), INK),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, INK),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ("TOPPADDING", (0, 0), (-1, 0), 5),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TEXTCOLOR", (0, 1), (-1, -1), INK),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, -1), (-1, -1), 0.6, INK),
            ]
        )
    )
    out = [t]
    if caption:
        out.append(Paragraph(caption, TBL_CAPTION))
    return out


# ----- content -----


def build_story() -> list:
    s: list = []

    # ---------- title block (no separate page; arxiv-style top-of-paper) ----------
    s.append(Spacer(1, 0.4 * inch))
    s.append(Paragraph(TITLE, T_TITLE))
    s.append(Paragraph(SUBTITLE, T_SUB))
    s.append(Paragraph("Danny Watkins", T_AUTHOR))
    s.append(Paragraph(
        "<font name='Courier'>github.com/danny-watkins/contextual-memory-architecture</font>",
        T_AFFIL,
    ))
    s.append(Paragraph(f"Version {VERSION} &nbsp;&middot;&nbsp; {TODAY}", T_DATE))

    # Abstract
    s.append(Paragraph("ABSTRACT", ABSTRACT_HEAD))
    s.append(Paragraph(
        "Modern AI agents are functionally stateless: they execute impressive work "
        "inside a single context window but fail to carry experience forward across "
        "tasks, sessions, and projects. Standard retrieval-augmented generation (RAG) "
        "treats memory as approximate-nearest-neighbor lookup over embedded chunks. "
        "This is a partial solution. Agent memory is relational, temporal, and "
        "cumulative; the most useful context for a task is rarely the nearest vector "
        "chunk - it is a decision linked to a project, a postmortem linked to a "
        "failure mode, or a pattern inferred across tasks. We propose Contextual "
        "Memory Architecture (CMA), a closed-loop, three-node memory layer composed "
        "of a Reasoner that decides what context matters, a Retriever that converts "
        "long-term memory into structured Context Specs via hybrid lexical-semantic "
        "search and graph traversal over an Obsidian-compatible markdown vault, and "
        "a Recorder that converts completed work back into structured durable memory "
        "under a confidence-gated write policy. CMA is local-first, framework-"
        "agnostic, and lightweight enough that every agent in a multi-agent system "
        "can carry its own vault. We describe the architecture, the retrieval and "
        "write algorithms, the evaluation harness, and the operational tooling for "
        "memory health and lifecycle curation. We provide a reference implementation "
        "in Python with 150 tests, a Model Context Protocol server exposing ten "
        "tools for any compatible agent, and a CLI. We discuss the architectural "
        "trajectory toward fractal composition of per-agent vaults into network-level "
        "memory graphs.",
        ABSTRACT_BODY,
    ))

    # ---------- 1. introduction ----------
    s.append(Paragraph("1.&nbsp;&nbsp;Introduction", H1))
    s.append(para(
        "Most production agents pay the same context-gathering cost on every task. "
        "Each session begins cold: prior architectural decisions, project conventions, "
        "user preferences, tool quirks, and recurring constraints must be re-discovered "
        "or re-supplied. The agent does not become meaningfully better with experience "
        "because it has no structured way to learn from its own work. This is the "
        "<i>stateless agent problem</i>, and standard RAG addresses only a thin slice "
        "of it.",
    ))
    s.append(Paragraph("1.1&nbsp;&nbsp;The limits of standard RAG", H2))
    s.append(para(
        "The canonical RAG pipeline embeds a query, retrieves the top-<i>k</i> nearest "
        "chunks by cosine similarity, and concatenates them into the prompt. This is "
        "effective for unstructured local document Q&amp;A but fails when the most "
        "useful context is structurally rather than semantically nearest. The decision "
        "that explains the current architecture is often a single short note linked "
        "from many places; the postmortem that explains a failure mode is rarely "
        "lexically similar to the new failure that occurred. Naive chunk retrieval "
        "discards the relational topology that human collaborators rely on. It also "
        "discards temporality: superseded decisions retrieve as eagerly as current "
        "ones, polluting context with stale guidance."
    ))
    s.append(Paragraph("1.2&nbsp;&nbsp;The missing write path", H2))
    s.append(para(
        "Most published memory systems concentrate on retrieval. Few treat the write "
        "path as a first-class function. But a system that retrieves without recording "
        "does not compound: it cannot learn from its own outputs because nothing of "
        "structural value persists. We argue that <i>memory formation</i> - the "
        "transformation of completed work into durable, retrievable structure under a "
        "controlled write policy - must be a peer node alongside retrieval, not a "
        "trailing log."
    ))
    s.append(Paragraph("1.3&nbsp;&nbsp;Contributions", H2))
    s.append(para(
        "This paper contributes: (1) a three-node closed-loop architecture (Reasoner, "
        "Retriever, Recorder) with explicit data contracts (TaskFrame, ContextSpec, "
        "CompletionPackage); (2) a retrieval pipeline that combines BM25L lexical "
        "scoring, optional dense embeddings, beam-pruned multi-hop graph traversal, "
        "and paragraph-level fragment extraction with cross-node deduplication; "
        "(3) a confidence-gated memory write policy that distinguishes always-write, "
        "draft, propose, and skip outcomes; (4) operational tooling for memory health "
        "observability and lifecycle curation; and (5) an open-source reference "
        "implementation with 150 tests, a Model Context Protocol server, and a CLI."
    ))
    s.append(Paragraph("1.4&nbsp;&nbsp;Lightweight and fractal", H2))
    s.append(para(
        "CMA is designed as the memory layer a single agent <i>carries with it</i>. "
        "Each agent in a multi-agent system has its own local vault; experiences do "
        "not cross-contaminate by default. A vault is a graph of notes; a graph of "
        "vaults is itself a graph. The same primitives - hybrid scoring, beam "
        "traversal, fragment extraction, context-spec assembly - apply at higher "
        "levels of composition, opening a path to federated retrieval across agent "
        "boundaries. The current reference implementation is the per-agent foundation; "
        "the cross-agent (fractal) layer is roadmap work."
    ))

    # ---------- 2. related work ----------
    s.append(Paragraph("2.&nbsp;&nbsp;Related Work", H1))
    s.append(para(
        "CMA builds on retrieval-augmented generation [Lewis et al., 2020], graph-"
        "augmented retrieval [Edge et al., 2024], persistent agent frameworks "
        "(LangGraph, AutoGen, CrewAI), knowledge graph systems, and the Model Context "
        "Protocol (Anthropic, 2024). It draws on personal knowledge management "
        "practices (Obsidian, Roam Research) for the substrate. Its contribution is "
        "not the invention of any of these elements but a closed-loop composition: "
        "the Reasoner-Retriever-Recorder triple specifically structured so that "
        "Recorder-written memory becomes useful Retriever input on subsequent tasks. "
        "Most prior systems implement two of the three nodes; few have explicit "
        "policies governing the write path."
    ))
    s.append(para(
        "We deliberately exclude an LLM-driven entity-extraction pass at index time "
        "(typical of automated GraphRAG pipelines). The substrate already contains the "
        "graph: wikilinks authored by humans (or by the agent under the Recorder's "
        "control) define edges, and YAML frontmatter defines node metadata. This is "
        "deliberate scope: CMA optimizes for inspectability and incremental compounding, "
        "not for one-shot extraction over an unstructured corpus."
    ))

    # ---------- 3. system architecture ----------
    s.append(Paragraph("3.&nbsp;&nbsp;System Architecture", H1))
    s.append(para(
        "CMA factors agent memory into three intelligent functions operating over a "
        "shared canonical substrate. Figure 1 shows the closed loop."
    ))

    s.extend(figure_box([
        "         Human / System Goal",
        "                  |",
        "                  v",
        "          +-------------+",
        "          |  Reasoner   |    frame goal, judge risk, request memory",
        "          +-------------+",
        "                  |",
        "                  v",
        "          +-------------+",
        "          |  Retriever  |    hybrid search + graph traversal",
        "          +-------------+",
        "                  |",
        "          context_spec.md",
        "                  |",
        "                  v",
        "          +-------------+",
        "          |  Reasoner   |    plan, act, supervise, synthesize",
        "          +-------------+",
        "                  |",
        "          completion_package",
        "                  |",
        "                  v",
        "          +-------------+",
        "          |  Recorder   |    write decisions, patterns, sessions",
        "          +-------------+",
        "                  |",
        "                  v",
        "          +-------------+",
        "          |  Retriever  |    re-index, link, validate",
        "          +-------------+",
        "                  |",
        "                  v",
        "       Better memory for next task",
    ], "Figure 1. Closed-loop CMA architecture. The Reasoner is the judgment node; "
       "the Retriever is the recall node; the Recorder is the formation node. "
       "Memory becomes context, context shapes action, action becomes memory."))

    s.append(Paragraph("3.1&nbsp;&nbsp;The Reasoner", H2))
    s.append(para(
        "The Reasoner is the judgment node. Given a goal, it produces a structured "
        "TaskFrame: task identifier, domain classification, risk level, a context "
        "request specifying query string, depth budget, beam width, and token budget, "
        "and a list of expected outputs. The Reasoner does not directly read or "
        "write the vault. It coordinates the other nodes through structured artifacts. "
        "This separation matters: it makes the agent's reasoning transparent (the "
        "TaskFrame is inspectable), reproducible (the same TaskFrame produces the same "
        "Context Spec), and policy-controllable (memory writes can require "
        "human approval at the TaskFrame level). The reference implementation models "
        "TaskFrame as a Pydantic v2 schema."
    ))

    s.append(Paragraph("3.2&nbsp;&nbsp;The Retriever", H2))
    s.append(para(
        "The Retriever transforms a TaskFrame into a Context Spec - a structured "
        "working-memory artifact, not a raw chunk dump. The Context Spec contains "
        "scored fragments with provenance, a relationship map of edges between "
        "included nodes, open questions, and exclusions (with reasons). It is "
        "designed to be inspectable, debuggable, reproducible, and testable. Section "
        "4 specifies the retrieval algorithm in detail."
    ))

    s.append(Paragraph("3.3&nbsp;&nbsp;The Recorder", H2))
    s.append(para(
        "The Recorder transforms a CompletionPackage - the structured output of a "
        "completed task - into vault writes under a memory write policy. It writes "
        "session notes (always), decision notes and pattern notes (gated by status "
        "and confidence), daily-log entries (always appended), and a JSONL audit "
        "trail. Section 5 details the write policy."
    ))

    s.append(Paragraph("3.4&nbsp;&nbsp;The vault as canonical substrate", H2))
    s.append(para(
        "All three nodes operate over a single Obsidian-compatible markdown vault. "
        "Markdown gives inspectability, YAML frontmatter gives machine-readable "
        "metadata, wikilinks (<font name='Courier'>[[Note]]</font>) give graph "
        "edges, folders give clusters, and git gives version history. Derived "
        "structures - the BM25 index, the embedding matrix, the NetworkX graph "
        "object, the retrieval log - live under <font name='Courier'>.cma/</font> "
        "and are fully rebuildable from the vault. This means memory survives "
        "index corruption, version upgrades, and tool changes; canonical truth is "
        "always the human-readable markdown."
    ))

    # ---------- 4. retrieval ----------
    s.append(Paragraph("4.&nbsp;&nbsp;The Retrieval Pipeline", H1))
    s.append(para(
        "Given a query <i>q</i> and a vault <i>V</i> producing a graph <i>G = (N, E)</i> "
        "of notes <i>N</i> linked by wikilinks <i>E</i>, the Retriever computes a "
        "Context Spec <i>S(q, V)</i> in five stages: (i) hybrid seed search, (ii) "
        "beam-pruned graph traversal, (iii) per-node final scoring, (iv) paragraph-"
        "level fragment extraction with cross-node deduplication, (v) Context Spec "
        "assembly with relationship map."
    ))

    s.append(Paragraph("4.1&nbsp;&nbsp;Hybrid lexical-semantic scoring", H2))
    s.append(para(
        "Each candidate node <i>n</i> receives a hybrid score combining a lexical "
        "score from BM25L and an optional dense semantic score from a configured "
        "embedder. BM25L's IDF formulation,"
    ))
    s.append(Paragraph(
        "IDF(t) = log( (N + 1) / (df(t) + 0.5) ),", EQUATION
    ))
    s.append(para(
        "is strictly positive and zero-floored: documents containing zero query terms "
        "score zero, and documents with terms appearing in many other documents are "
        "softly downweighted but never produce negative IDF. This matters in our "
        "setting because wikilink anchor text duplicates terms across linked notes; "
        "with BM25Okapi's IDF, half-the-corpus terms produce negative scores that "
        "made every doc rank similarly. Section 11.1 discusses this choice in detail."
    ))
    s.append(para(
        "We concatenate the title three times before the body during tokenization. "
        "This is a cheap field-weighting heuristic that gives title tokens a stronger "
        "BM25 signal without learning a separate field-weighted index. It interacts "
        "well with BM25L's TF saturation behavior."
    ))
    s.append(para(
        "When an embedder is configured, the semantic score is the cosine similarity "
        "between the L2-normalized query embedding and the L2-normalized note "
        "embedding. Both lexical and semantic scores are normalized to [0, 1] per "
        "query (max-normalization on the lexical side, native cosine on the semantic "
        "side). The hybrid score combines them linearly:"
    ))
    s.append(Paragraph(
        "node_score = &alpha; &middot; sem(n, q) + (1 &minus; &alpha;) &middot; lex(n, q)",
        EQUATION,
    ))
    s.append(para(
        "with default <i>&alpha; = 0.7</i> favoring semantic similarity. When only "
        "one modality is available (semantic = 0 or lexical = 0), the present "
        "modality carries full weight rather than being averaged with zero - this "
        "prevents the hybrid score from collapsing in BM25-only mode."
    ))

    s.append(Paragraph("4.2&nbsp;&nbsp;Metadata boosts and depth decay", H2))
    s.append(para(
        "Raw hybrid scores are modulated by per-record metadata boosts (Table 1) and "
        "by depth decay across graph traversal:"
    ))
    s.append(Paragraph(
        "final_score(n) = node_score(n) &middot; metadata_boost(n) &middot; (decay)<sup>depth(n)</sup>",
        EQUATION,
    ))
    s.append(para(
        "with default <i>decay = 0.80</i>. Metadata boosts encode domain-relevant "
        "preferences: an accepted decision should be retrieved more eagerly than a "
        "rejected one; a superseded decision should be heavily penalized; a human-"
        "verified note carries an additional boost; high-confidence records boost; "
        "low-confidence records penalize."
    ))
    s.extend(make_table(
        ["Condition",                                "Multiplicative boost"],
        [
            ["type = decision &amp; status = accepted",         "+0.10"],
            ["type = decision &amp; status = superseded",       "&minus;0.50"],
            ["type = decision &amp; status = rejected",         "&minus;0.30"],
            ["status = archived",                                "&minus;0.20"],
            ["human_verified = true",                            "+0.10"],
            ["confidence &ge; 0.85",                             "+0.08"],
            ["confidence &lt; 0.30",                             "&minus;0.10"],
        ],
        col_widths=[3.5 * inch, 1.6 * inch],
        caption="Table 1. Metadata-derived multiplicative boosts applied to "
                "hybrid node scores. Boosts compose; the final boost is clamped at 0.",
    ))

    s.append(Paragraph("4.3&nbsp;&nbsp;Beam-pruned graph traversal", H2))
    s.append(para(
        "Seed nodes are selected from the union of top-<i>k</i> hybrid hits whose "
        "scores meet the seed threshold (default 0.30). From each seed, the Retriever "
        "expands outward over both outgoing and incoming edges (back-link traversal "
        "is symmetric in our model: a backlink is as informative as a forward link "
        "for context assembly). At each depth, candidates are beam-pruned by "
        "inherited parent score; up to <i>beam_width</i> children survive. Algorithm "
        "1 summarizes."
    ))
    s.extend(algo("Algorithm 1. Beam-pruned multi-hop traversal.",
        "Input:   query q, graph G, seed set S0, max_depth D, beam_width B\n"
        "Output:  list of (node, depth) candidates\n"
        "\n"
        "1.  visited <- { (s, 0) for s in S0 }\n"
        "2.  frontier <- [(s, score(s, q))  for s in S0]\n"
        "3.  for d in 1..D:\n"
        "4.      next_candidates <- {}\n"
        "5.      for (n, parent_score) in frontier:\n"
        "6.          for m in neighbors(n):                 # forward AND backward edges\n"
        "7.              if m not in visited and exists(m):\n"
        "8.                  next_candidates[m] <- max(next_candidates.get(m, 0), parent_score)\n"
        "9.      ranked  <- sort_desc(next_candidates) [: B]\n"
        "10.     visited <- visited UNION { (m, d) for (m, _) in ranked }\n"
        "11.     frontier <- ranked\n"
        "12.     if frontier is empty: break\n"
        "13. return [(n, d) for (n, d) in visited]"))
    s.append(para(
        "Critically, the seed threshold gates seed selection only - traversed nodes "
        "are admitted to the candidate set unconditionally (within depth and beam "
        "budgets). This is deliberate: the entire purpose of GraphRAG is that "
        "graph-adjacent context earns inclusion through topology, not through direct "
        "lexical or semantic match. Filtering traversed nodes by the same threshold "
        "as seeds collapses the architecture into vector RAG. We discuss this design "
        "choice in Section 11.2."
    ))

    s.append(Paragraph("4.4&nbsp;&nbsp;Fragment extraction and deduplication", H2))
    s.append(para(
        "Note bodies are typically too long to inject in full. For each surviving "
        "candidate, the body is split into paragraphs, each paragraph is scored "
        "against the query token set by Jaccard-style overlap, and the top "
        "<i>m</i> paragraphs (default <i>m = 3</i>) above the fragment threshold "
        "(default 0.42) are selected. Seed nodes are exempt from the fragment "
        "threshold to ensure that the strongest matches contribute at least one "
        "fragment regardless of paragraph-level overlap."
    ))
    s.append(para(
        "Across nodes, fragments are deduplicated by token-set Jaccard similarity "
        "(threshold 0.85): when multiple notes contain near-identical paragraphs "
        "(common in well-linked vaults), the highest-scoring instance is retained "
        "and others are dropped. This keeps the Context Spec compact when graph "
        "traversal surfaces structurally redundant text."
    ))
    s.append(para(
        "Plainly: a <i>fragment</i> is a single paragraph (or short section) of "
        "text that the Retriever decided was relevant to the query. The "
        "Retriever does not paste whole notes into the Context Spec - it "
        "cherry-picks paragraphs. A 466-token decision note with five sections "
        "might contribute three fragments totaling 217 tokens, leaving the other "
        "249 tokens of the note out of the spec. The dashboard surfaces this "
        "per-source breakdown (&sect;5.9) so the user can see which fragments "
        "were pulled and what fraction of each source note made it into the "
        "agent's context."
    ))
    s.append(para(
        "Before scoring, paragraphs that match structural-boilerplate patterns are "
        "dropped from the candidate pool: markdown headings "
        "(<font name='Courier'>^#+\\s</font>), ingest attribution lines "
        "(<font name='Courier'>^From \\[\\[X\\]\\] / path</font>), and lone code "
        "fences. These short paragraphs match query keywords on superficial overlap "
        "(<font name='Courier'>'# notify'</font> matches a query about "
        "<font name='Courier'>notify.py</font>) but carry no real content. Filtering "
        "them at the source means the fragment selection rewards substantive "
        "paragraphs over markdown structure. If every paragraph in a note is "
        "boilerplate the filter degrades gracefully and includes the original "
        "set, preserving the no-empty-result contract."
    ))

    s.append(Paragraph("4.5&nbsp;&nbsp;Context Spec assembly", H2))
    s.append(para(
        "The final Context Spec records the spec identifier, task identifier, query, "
        "generation timestamp, full retrieval parameters (for reproducibility), the "
        "ordered list of fragments with provenance and scores, the relationship map "
        "(edges between included nodes), open questions if the Reasoner declared any, "
        "and exclusions with reasons. The assembly is deterministic given the same "
        "vault state, parameters, and embedder."
    ))

    s.append(Paragraph("4.6&nbsp;&nbsp;Complexity and scaling", H2))
    s.append(para(
        "BM25L scoring is <i>O(|q| &middot; |N|)</i> on the corpus; cosine similarity "
        "via dense matrix multiplication over normalized embeddings is <i>O(|N| &middot; "
        "d)</i> for embedding dimension <i>d</i>; graph traversal with beam <i>B</i> "
        "and depth <i>D</i> is <i>O(B<sup>D</sup>)</i> in the worst case but in "
        "practice is bounded by the graph density and visited-set deduplication. For "
        "vaults below approximately 100K notes on commodity hardware, the entire "
        "pipeline executes in under one second per query without approximate-nearest-"
        "neighbor structures. Section 10 provides empirical scaling characteristics."
    ))

    # ---------- 5. memory formation ----------
    s.append(Paragraph("5.&nbsp;&nbsp;Memory Formation", H1))
    s.append(para(
        "Recording is a constrained transformation. Not every output of every task "
        "should become durable memory - a system that records indiscriminately "
        "produces vault pollution and degrades retrieval quality over time. We "
        "specify a memory write policy that maps each item in a CompletionPackage "
        "to one of four outcomes: WRITE (commit to vault as active), DRAFT (commit "
        "with status = draft), PROPOSE (write to a proposals folder requiring "
        "human approval), or SKIP (do not record)."
    ))

    s.append(Paragraph("5.1&nbsp;&nbsp;Confidence calibration", H2))
    s.append(para(
        "We use a confidence band model. Records with confidence below 0.25 are "
        "considered noise and skipped. Confidence in [0.25, 0.50) indicates weak "
        "signal: such records are routed to proposals (human approval gate). "
        "Confidence in [0.50, 0.75) is tentative inference: written as drafts. "
        "Confidence at or above 0.75 indicates strong evidence: written as active. "
        "These thresholds are calibrated heuristically; the system exposes them as "
        "configuration."
    ))

    s.append(Paragraph("5.2&nbsp;&nbsp;Status-aware decision routing", H2))
    s.append(para(
        "For Decision records, status overrides confidence in some cases. An "
        "accepted decision is always written (even at low confidence: it represents "
        "a human-anchored commitment); a rejected decision is also always written "
        "(useful negative evidence for future reasoning); a superseded decision is "
        "written or proposed based on configuration (some operators require human "
        "approval for any supersedure). Algorithm 2 specifies the full routing."
    ))
    s.extend(algo("Algorithm 2. Memory write policy for Decision records.",
        "function policy(decision, config):\n"
        "    if decision.confidence < 0.25:\n"
        "        return SKIP, 'below confidence floor'\n"
        "    if decision.status == 'accepted':\n"
        "        return WRITE, 'accepted decision'\n"
        "    if decision.status == 'rejected':\n"
        "        return WRITE, 'rejected (recorded for posterity)'\n"
        "    if decision.status == 'superseded':\n"
        "        if 'supersede_decision' in config.require_human_approval_for:\n"
        "            return PROPOSE, 'supersedure requires approval'\n"
        "        return WRITE\n"
        "    # status == 'proposed'\n"
        "    if decision.confidence >= 0.75:\n"
        "        return WRITE, 'high-confidence proposal'\n"
        "    if decision.confidence >= 0.50:\n"
        "        return DRAFT, 'tentative proposal'\n"
        "    return PROPOSE, 'weak proposal needs human approval'"))

    s.append(Paragraph("5.3&nbsp;&nbsp;Pattern routing", H2))
    s.append(para(
        "Patterns are inferred (not human-stated), so they are held to a higher bar. "
        "Strong-evidence patterns (confidence &ge; 0.75) auto-write. Tentative "
        "patterns route to drafts unless <i>low_confidence_pattern</i> is in the "
        "human-approval set, in which case they route to proposals. Weak-signal "
        "patterns always go to proposals."
    ))

    s.append(Paragraph("5.4&nbsp;&nbsp;Always-written artifacts", H2))
    s.append(para(
        "Every CompletionPackage produces exactly one session note (in "
        "<font name='Courier'>vault/002-sessions/</font>) with links to all decisions "
        "and patterns recorded from the same task. Every CompletionPackage also "
        "appends a single entry to today's daily log "
        "(<font name='Courier'>vault/010-daily-log/&lt;date&gt;.md</font>). The "
        "Recorder additionally writes a JSONL audit trail under "
        "<font name='Courier'>recorder/write_logs/&lt;task_id&gt;-write-log.jsonl</font>"
        " recording the action and reason for every item the policy considered, "
        "including skipped ones. This audit trail is what enables the Reasoner to "
        "later assess <i>which</i> records earned their place and which are "
        "candidates for archival."
    ))

    s.append(Paragraph("5.5&nbsp;&nbsp;Duplicate handling", H2))
    s.append(para(
        "When a Decision or Pattern shares a sanitized title with an existing vault "
        "note, the Recorder skips the write rather than overwriting. Resolution of "
        "intentional supersedure is the operator's responsibility (Section 9.2). "
        "This conservative default prevents accidental loss of human edits."
    ))

    s.append(Paragraph("5.6&nbsp;&nbsp;Automatic related-note linking", H2))
    s.append(para(
        "Structural backlinks (session &harr; decision/pattern, daily log &rarr; session) "
        "give the graph a star pattern around each task, but they do not connect "
        "thematically related notes across tasks. Without further work, a vault "
        "tends to grow as disconnected stars. To counter this, the Recorder runs a "
        "lightweight similarity lookup at write time: it builds an in-memory BM25 "
        "index over all existing decisions and patterns, scores the new note's "
        "title-and-rationale text against the corpus, and appends the top-<i>k</i> "
        "titles above a similarity threshold as a <font name='Courier'>## Related</font> "
        "section of <font name='Courier'>[[wikilinks]]</font> in the rendered note "
        "(default k = 3, threshold = 0.4 normalized BM25 score)."
    ))
    s.append(para(
        "The lookup is best-effort: if the vault is empty, unparseable, or the "
        "BM25 module is unavailable, the Recorder writes the note without a Related "
        "section rather than failing. No new dependencies are introduced - the same "
        "BM25 implementation used by the Retriever (Section 4.1) is reused. The "
        "computational cost is negligible at typical vault scales (a few milliseconds "
        "per record_completion call for vaults under ten thousand decision/pattern "
        "notes)."
    ))
    s.extend(algo("Algorithm 3. Auto-related linking during a Recorder write.",
        "function find_related(new_text, vault, k=3, threshold=0.4):\n"
        "    existing = [r for r in vault.records\n"
        "                if r.type in {'decision', 'pattern'}]\n"
        "    if existing is empty: return []\n"
        "    index = BM25Index(existing)\n"
        "    hits = index.search(new_text, top_k=2k)\n"
        "    related = []\n"
        "    for (record_id, score) in hits:\n"
        "        if score < threshold: continue\n"
        "        title = vault.title_of(record_id)\n"
        "        if title == new_text.title: continue   # no self-links\n"
        "        related.append(title)\n"
        "        if len(related) >= k: break\n"
        "    return related"))
    s.append(para(
        "The effect on graph density is concrete: in a vault with a hundred "
        "decisions covering five distinct domains, a new decision in one of the "
        "domains will typically attract three to five related links into that "
        "cluster, whereas before it would have been an isolated leaf with only its "
        "session backlink. This keeps retrieval recall high as the vault grows: the "
        "graph traversal in Section 4.2 has more edges to follow, so a query that "
        "lands on any node in the cluster can reach the rest within the configured "
        "depth."
    ))

    s.append(Paragraph("5.7&nbsp;&nbsp;Automatic firing via host hooks", H2))
    s.append(para(
        "The three nodes of &sect;3.1 (Reasoner, Retriever, Recorder) must fire on "
        "every task to make memory part of the agent's default loop rather than an "
        "optional tool the agent might or might not remember to call. We achieve "
        "this without coupling the engine to any one host runtime by exposing two "
        "thin hook entry points - <font name='Courier'>cma hook user-prompt</font> "
        "and <font name='Courier'>cma hook stop</font> - and letting the host's hook "
        "system trigger them at task boundaries. For Claude Code (the reference host), "
        "<font name='Courier'>cma add</font> registers these in "
        "<font name='Courier'>.claude/settings.json</font> under "
        "<font name='Courier'>UserPromptSubmit</font> and <font name='Courier'>Stop</font>."
    ))
    s.append(para(
        "The UserPromptSubmit hook runs the FULL Retriever pipeline of &sect;4 end-to-end: "
        "hybrid BM25+embedding seed selection (&sect;4.1), beam-pruned graph traversal "
        "(&sect;4.2), paragraph-level fragment extraction (&sect;4.4), Context Spec "
        "assembly (&sect;4.5), and persistence to "
        "<font name='Courier'>vault/008-context-specs/</font>. Per-hook cost is "
        "approximately 2 to 3 seconds dominated by loading the sentence-transformers "
        "model into the new Python process; this falls inside the agent's normal "
        "first-token latency and is not user-visible in practice. The hook also "
        "captures the prompt to "
        "<font name='Courier'>vault/000-inbox/prompts/&lt;date&gt;/</font> with "
        "<font name='Courier'>status: noise</font> for the inbox-promotion mechanism "
        "of &sect;5.8, and the persisted spec note immediately joins the vault as a "
        "first-class memory artifact - future retrieves can find prior specs as "
        "relevant sources, compounding the agent's own context-gathering work."
    ))
    s.append(para(
        "Two filters narrow the hook's seed pool to keep auto-fire signal high. "
        "First, inbox prompt notes (<font name='Courier'>status: noise</font>) are "
        "excluded: matching against them would be circular, since the just-captured "
        "prompt would otherwise rank itself first. Second, prior "
        "<font name='Courier'>context_spec</font> notes are excluded: their bodies "
        "contain query-keyword-heavy structural metadata "
        "(<font name='Courier'>## Sources</font>, "
        "<font name='Courier'>From [[X]] / path</font>) that crowds out primary source "
        "content under hybrid scoring. Agents that explicitly want the spec-feeds-spec "
        "flywheel call <font name='Courier'>mcp__cma__retrieve</font> directly, which "
        "operates on the unfiltered pool."
    ))
    s.append(para(
        "The Stop hook appends a session summary to "
        "<font name='Courier'>vault/002-sessions/&lt;session-id&gt;.md</font>. This is "
        "mechanical capture only: no LLM call, no decision extraction. Promoting a "
        "session into structured memory (decisions, patterns, postmortems) remains "
        "the Recorder sub-agent's job, invoked deliberately when the agent has work "
        "worth committing per the confidence-gated policy of &sect;5.1-5.6."
    ))
    s.append(para(
        "The hook contract is intentionally portable: a host integrator on any other "
        "framework wires their equivalent of pre-step and post-step hooks to invoke "
        "the same two CLI commands. The CMA engine itself remains host-agnostic; "
        "only the registration step in <font name='Courier'>cma add</font> is "
        "Claude Code-specific."
    ))

    s.append(Paragraph("5.8&nbsp;&nbsp;The prompt inbox and noise promotion", H2))
    s.append(para(
        "Capturing every prompt - including ones that turn out to be irrelevant - "
        "is a small cost (one markdown file with frontmatter, a few hundred bytes) "
        "with a large optionality payoff. Inbox prompts form their own cluster in "
        "the graph view (color-grouped distinctly from active notes) and are "
        "searchable with the same primitives that operate on the rest of the vault. "
        "The Curator sub-agent periodically scans the inbox for recurring themes: "
        "when the same question has appeared in 3+ distinct sessions, it proposes "
        "promotion - either to a <i>pattern</i> note (if the recurrence reflects a "
        "behavior the user keeps doing) or to a <i>concept</i> note (if it reflects "
        "a new vault entity worth naming). The host agent approves the promotion; "
        "the originals get <font name='Courier'>status: promoted</font> and link to "
        "the new note as <font name='Courier'>evidence</font>. Nothing is thrown "
        "away; nothing pretends to be more than it is."
    ))

    s.append(Paragraph("5.9&nbsp;&nbsp;Memory log and verification dashboard", H2))
    s.append(para(
        "Every meaningful CMA operation - search, retrieve, record, index, ingest, "
        "bootstrap - appends one event to "
        "<font name='Courier'>cma/memory_log/activity.jsonl</font> and triggers the "
        "regeneration of <font name='Courier'>cma/memory_log/dashboard.html</font>. "
        "The dashboard is a single self-contained HTML file: vanilla CSS and "
        "JavaScript, no server, no CDN, no build step. The user opens it once in any "
        "browser and leaves it open; an embedded "
        "<font name='Courier'>&lt;meta http-equiv=&quot;refresh&quot;&gt;</font> tag "
        "reloads the page every five seconds, and JavaScript restores scroll "
        "position so the reload is visually invisible."
    ))
    s.append(para(
        "Each event renders as a row showing time, type, summary, and "
        "<font name='Courier'>[[wikilink]]</font>-style links to every artifact "
        "produced. A retrieve or auto-fire prompt event links to the Context Spec "
        "note it wrote; a record event links to the decision, pattern, session, "
        "and daily-log notes it produced. Links open in Obsidian via the "
        "<font name='Courier'>obsidian://</font> protocol when the user has Obsidian "
        "installed, falling back to <font name='Courier'>file://</font> otherwise. "
        "The dashboard groups events by session (one Claude Code restart = one "
        "session) and supports filtering by event type, session, and free-text "
        "query."
    ))
    s.append(para(
        "Per-source token accounting. For every retrieve event, the dashboard "
        "renders one row per source node the Retriever pulled fragments from, "
        "with three pieces of provenance metadata: tokens extracted (sum of "
        "<font name='Courier'>len(text)/4</font> across that source's fragments), "
        "tokens total (the source note's full token count, same approximation), "
        "and percent of the document used. A user can tell at a glance whether "
        "the Retriever pulled a tight slice of a long note (e.g., "
        "<font name='Courier'>notification_channels &middot; 82/507 tokens (16.3%)</font>) "
        "or essentially the whole short note (<font name='Courier'>classify "
        "&middot; 162/249 tokens (65.3%)</font>). Each source row also exposes a "
        "&quot;view fragments&quot; link that opens the persisted spec.md - the "
        "user can jump from a one-line summary to the exact paragraphs the "
        "Retriever extracted, organized under "
        "<font name='Courier'>### From [[source_title]]</font> headings inside the spec."
    ))
    s.append(para(
        "The design choice of static-HTML over a live web server is deliberate: "
        "CMA installs into many agent projects, and a per-project background "
        "server creates &quot;which port, did I forget to start it&quot; friction. "
        "Static regeneration is cheap (~10 ms per event for a few hundred events) "
        "and the meta-refresh keeps the page current without a long-running process. "
        "The same JSONL log is also exposed via the <font name='Courier'>cma "
        "activity</font> CLI command for terminal users; both surfaces read the "
        "same source of truth."
    ))
    s.append(para(
        "The activity log is the primary mechanism for real-life verification of a "
        "CMA install. A user opens the dashboard, runs a few prompts in their host "
        "agent (&quot;search the vault for X&quot;, &quot;retrieve context for Y&quot;, "
        "&quot;record this decision&quot;), and watches the events stream in with "
        "clickable links to every artifact produced. The Obsidian graph view "
        "(&sect;7.3) provides the structural view; the activity dashboard provides "
        "the temporal view; together they make the otherwise-invisible work of the "
        "memory layer legible."
    ))

    # ---------- 6. local-first substrate ----------
    s.append(Paragraph("6.&nbsp;&nbsp;Local-First Substrate", H1))
    s.append(Paragraph("6.1&nbsp;&nbsp;Vault layout", H2))
    s.append(para(
        "All CMA-managed files live under a single <font name='Courier'>cma/</font> "
        "subdirectory of the host agent's project, keeping the project root uncluttered. "
        "Inside <font name='Courier'>cma/</font>: a single configuration file "
        "(<font name='Courier'>config.yaml</font>), a <font name='Courier'>vault/</font> "
        "subdirectory holding the canonical markdown memory store, a "
        "<font name='Courier'>cache/</font> directory for derived state (BM25, "
        "embeddings, graph manifest), and a <font name='Courier'>memory_log/</font> "
        "directory for the operational activity stream and its visual dashboard. "
        "The vault is organized into thirteen numbered subfolders "
        "(<font name='Courier'>000-inbox</font> through <font name='Courier'>011-archive</font>) "
        "corresponding to canonical note types: inbox, projects, sessions, decisions, "
        "patterns, people, tools, codebase, context-specs, evals, daily-log, archive. "
        "The numeric prefixes preserve sort order in any file browser and in Obsidian."
    ))
    s.extend(figure_box([
        "  agent-project/",
        "    cma/",
        "      config.yaml",
        "      vault/                    # canonical markdown memory + .obsidian/",
        "        000-inbox/ ... 020-sources/",
        "      cache/                    # BM25, embeddings, graph state (derived)",
        "      memory_log/               # operational activity stream + dashboard",
        "        activity.jsonl",
        "        dashboard.html",
        "        write_logs/  proposals/",
        "    .claude/agents/cma-*.md     # Claude Code requires .claude/ at root",
        "    CLAUDE.md                   # Claude Code requires CLAUDE.md at root",
        "    .mcp.json                   # Claude Code requires .mcp.json at root",
    ], "Figure 4. Project layout after cma add. Three top-level subdirectories under "
       "cma/: vault (canonical), cache (derived), memory_log (operational). The three "
       "Claude Code files at the project root are required by the host runtime."))

    s.append(Paragraph("6.2&nbsp;&nbsp;Derived state and operational logs", H2))
    s.append(para(
        "<font name='Courier'>cma/cache/</font> contains the BM25 pickle, the embedding "
        "matrix as a NumPy <font name='Courier'>.npy</font> file with associated "
        "<font name='Courier'>doc_ids.json</font> and <font name='Courier'>meta.json</font>, "
        "the graph node manifest as JSON, and the retrieval log as JSONL. Every "
        "artifact is regenerable from the vault by running <font name='Courier'>cma "
        "index</font>. This invariant - <i>vault is canonical, cache/ is derived</i> - "
        "is enforced architecturally: the Recorder writes only to the vault, never to "
        "<font name='Courier'>cache/</font>."
    ))
    s.append(para(
        "<font name='Courier'>cma/memory_log/</font> holds the user-facing activity "
        "stream: <font name='Courier'>activity.jsonl</font> is an append-only log of "
        "every search, retrieve, record, ingest, and index operation; "
        "<font name='Courier'>dashboard.html</font> is a self-contained visual viewer "
        "regenerated after every event (&sect;5.7); <font name='Courier'>write_logs/</font> "
        "and <font name='Courier'>proposals/</font> are the Recorder's per-task audit "
        "trails and policy-gated write proposals respectively."
    ))

    s.append(Paragraph("6.3&nbsp;&nbsp;Robust parsing", H2))
    s.append(para(
        "Vault loading (<font name='Courier'>parse_vault</font>) is best-effort: any "
        "individual note with malformed YAML frontmatter is degraded to an "
        "empty-frontmatter record (the body still participates in BM25, embeddings, "
        "and graph construction) rather than failing the whole vault load. One bad "
        "file - typically an agent-written frontmatter with an unescaped Windows "
        "path or a multi-line value the YAML scanner rejects - cannot take the memory "
        "layer offline. The recorder writes new frontmatter through "
        "<font name='Courier'>python-frontmatter</font> which always produces "
        "well-formed YAML, so this failure mode is bounded to hand- or agent-edited "
        "notes."
    ))

    s.append(Paragraph("6.4&nbsp;&nbsp;Portability", H2))
    s.append(para(
        "Because the vault is plain markdown with YAML frontmatter and wikilinks, it "
        "is portable across machines (a directory copy), version-controllable with "
        "git (a directory <font name='Courier'>git add</font>), inspectable with any "
        "text editor, and openable as an Obsidian vault for visual graph navigation. "
        "Migration to a future format is a markdown transform, not a database migration."
    ))

    # ---------- 7. per-agent + fractal ----------
    s.append(Paragraph("7.&nbsp;&nbsp;Per-Agent Topology and Fractal Composition", H1))
    s.append(Paragraph("7.1&nbsp;&nbsp;Isolation by default", H2))
    s.append(para(
        "Each agent in a multi-agent system is provisioned with its own CMA project. "
        "Its vault holds the agent's decisions, sessions, and patterns; experiences "
        "do not cross-contaminate to other agents in the same system. This "
        "differs from the typical 'shared vector store' architecture and is "
        "deliberate: an architecture decision recorded by Agent A is part of A's "
        "epistemic state and may be wrong, controversial, or scoped to A's role. "
        "Sharing it with Agent B by default is a privacy and correctness leak."
    ))

    s.append(Paragraph("7.2&nbsp;&nbsp;Fractal composition", H2))
    s.append(para(
        "The same primitives that operate on a vault of notes can operate on a graph "
        "of vaults. Treat each per-agent vault as a node in a higher-order graph "
        "with explicit edges for sharing relationships (collaborator, supervisor, "
        "domain peer). The hybrid scoring formula generalizes; the beam-pruned "
        "traversal generalizes; the Context Spec generalizes. The fractal layer is "
        "future work in the reference implementation but does not require "
        "architectural changes - it is a recursion of the existing primitives."
    ))

    s.extend(figure_box([
        "    +---------+  +---------+  +---------+",
        "    | Agent A |  | Agent B |  | Agent C |",
        "    |  vault  |  |  vault  |  |  vault  |",
        "    +---------+  +---------+  +---------+",
        "         \\           |           /",
        "          \\          |          /",
        "           \\         |         /",
        "          +-------------------+",
        "          |  Network graph    |",
        "          |  (vaults as nodes,",
        "          |   typed edges     |",
        "          |   between agents) |",
        "          +-------------------+",
    ], "Figure 2. Fractal composition of per-agent vaults into a network-level "
       "memory graph. Each per-agent vault becomes a single node; edges between "
       "vaults represent typed sharing relationships."))

    s.append(Paragraph("7.3&nbsp;&nbsp;Integration model", H2))
    s.append(para(
        "CMA ships as a drop-in bundle installed by a single command, <i>cma add</i>. "
        "Run from any directory, it produces the layout shown in Figure 4 (&sect;6.1): "
        "a single <font name='Courier'>cma/</font> subdirectory holding the vault, "
        "config, node working dirs, and cache, plus three Claude Code-required files "
        "at the project root (<font name='Courier'>CLAUDE.md</font> with a prompt block, "
        "<font name='Courier'>.claude/agents/</font> with four pre-built sub-agents - "
        "bootstrap for one-time vault training, research for deep retrieval, recorder "
        "for write-back, curator for hygiene - and <font name='Courier'>.mcp.json</font> "
        "registering the CMA MCP server). The default scope is project-local, "
        "preserving the per-agent isolation of &sect;7.1. A --user flag installs at "
        "user scope, appropriate when a single shared vault should be available across "
        "all sessions of one user."
    ))
    s.append(para(
        "The host agent is the Reasoner from &sect;3.1: it reads the prompt block, "
        "decides when memory matters, and dispatches to sub-agents or MCP tools. "
        "The bundle teaches the host how to use CMA; the host decides when. This "
        "intentionally avoids tool-call hooks and session interceptors, which would "
        "bypass the agent's autonomy and couple the integration to a specific runtime."
    ))
    s.extend(figure_box([
        "  pip install contextual-memory-architecture[mcp]",
        "  cd <agent-project>",
        "  cma add",
        "    -> scaffolds ./cma/ (vault, config, node folders, cache)",
        "    -> writes CLAUDE.md, .claude/agents/, .mcp.json",
        "    -> copies .obsidian/ graph config into the new vault",
        "    -> ingests the agent's own source files into cma/vault/020-sources/",
        "    -> builds BM25 + embeddings + graph (cma/cache/)",
        "  # open Claude Code in <agent-project> for memory-aware sessions",
        "  # open Obsidian on <agent-project>/cma/vault for the live graph view",
    ], "Figure 3. The full integration ceremony, executed by a single command. "
       "cma add is idempotent; re-running updates the prompt block, copies any "
       "new bundle agents, and re-indexes."))
    s.append(para(
        "The MCP server defers initialization until first tool call so the stdio "
        "handshake completes within the host's connect timeout (the embedding model "
        "cold-start can exceed 30 seconds). The server holds Retriever and Recorder "
        "state for the lifetime of the process; subsequent tool calls in a session "
        "see a warm index."
    ))
    s.append(para(
        "Auto-ingestion of the host project at <i>cma add</i> time means the graph "
        "view in Obsidian shows real structure - decisions, design docs, code, and "
        "their wikilink edges - on first open, not an empty scaffold. The bundled "
        "<font name='Courier'>.obsidian/graph.json</font> ships color groups for the "
        "retrieve-count heatmap (faded &rarr; mid &rarr; bright green), red "
        "<font name='Courier'>context_spec</font> nodes, the yellow "
        "<font name='Courier'>cma_active</font> demo cursor, and folder-based colors "
        "for the canonical 020-prefixed vault layout. The user opens Obsidian, "
        "selects 'Open folder as vault' on <font name='Courier'>cma/vault</font>, and "
        "the visualization is immediately wired up; no per-vault configuration."
    ))

    # ---------- 8. evaluation ----------
    s.append(Paragraph("8.&nbsp;&nbsp;Evaluation", H1))
    s.append(Paragraph("8.1&nbsp;&nbsp;Modes", H2))
    s.append(para(
        "We define four evaluation modes for ablation: NO_MEMORY (control: empty "
        "retrieval), VECTOR_ONLY (hybrid scoring with traversal disabled, "
        "<i>max_depth = 0</i>), GRAPHRAG (the full Retriever, no Recorder write-back), "
        "and FULL_CMA (Retriever plus Recorder writes between tasks for longitudinal "
        "evaluation). The framework provides BenchmarkQuery, BenchmarkResult, and "
        "BenchmarkRun primitives to support all four."
    ))

    s.append(Paragraph("8.2&nbsp;&nbsp;Retrieval metrics", H2))
    s.append(para(
        "We track Recall@<i>k</i>, Precision@<i>k</i>, and Mean Reciprocal Rank as "
        "standard retrieval metrics. We add two CMA-specific metrics: the Memory "
        "Usefulness Score (MUS) and the Context Efficiency Score (CES)."
    ))
    s.append(Paragraph(
        "MUS = +2 r<sub>used</sub> + 2 d<sub>applied</sub> + 2 f<sub>avoided</sub> "
        "&minus; 1 r<sub>irrelevant</sub> &minus; 3 c<sub>missed</sub> &minus; 2 s<sub>stale</sub>",
        EQUATION,
    ))
    s.append(para(
        "where the terms are counts: relevant memories used, prior decisions applied, "
        "prior failures avoided, irrelevant items included, critical memories missed, "
        "and stale-or-superseded memories incorrectly used. The asymmetric weighting "
        "(missing critical memory is weighted three, including irrelevant memory is "
        "weighted one) reflects the operational asymmetry: a missed critical decision "
        "can cause repeat work or incorrect reasoning, while extra context only costs "
        "tokens."
    ))
    s.append(Paragraph(
        "CES = used_fragments / included_fragments",
        EQUATION,
    ))
    s.append(para(
        "Higher CES means tighter Context Specs without sacrificing task success - "
        "the Retriever is improving if specs become smaller while quality stays flat "
        "or improves."
    ))

    s.append(Paragraph("8.3&nbsp;&nbsp;Sample run", H2))
    s.append(para(
        "On the example vault shipped with the reference implementation (4 notes "
        "across decisions and patterns, 8 wikilink edges), running the included "
        "benchmark suite (3 queries) in GRAPHRAG mode yields mean Recall@5 = 1.0, "
        "MRR = 1.0, mean fragments = 6, mean unique sources = 3.67, mean estimated "
        "token consumption per spec = 133. While this small a vault is not a serious "
        "evaluation, it confirms end-to-end pipeline correctness."
    ))

    # ---------- 9. operations ----------
    s.append(Paragraph("9.&nbsp;&nbsp;Operational Concerns", H1))
    s.append(Paragraph("9.1&nbsp;&nbsp;Health observability", H2))
    s.append(para(
        "The <font name='Courier'>cma health</font> command produces a structured "
        "report covering vault size by folder, derived index footprint by component, "
        "graph density (orphan rate, broken-link rate, average degree), and "
        "retrieval activity (event count, last-7-days rate, most-retrieved notes, "
        "never-retrieved notes). Soft thresholds emit warnings: vault &gt; 50K notes, "
        "embeddings &gt; 200 MB, orphan rate &gt; 30%, broken-link rate &gt; 5%, "
        "never-retrieved rate &gt; 70%. The thresholds are guidance, not policy: a "
        "research agent with a high never-retrieved rate may simply have not yet "
        "needed the memory, and forced archival would be premature."
    ))
    s.append(para(
        "Each <font name='Courier'>retrieve()</font> call appends a JSON line to "
        "<font name='Courier'>.cma/state/retrieval_log.jsonl</font> with timestamp, "
        "query, fragment count, token estimate, and the source note titles. This log "
        "is the source-of-truth for cold-note detection and for the most-/never-"
        "retrieved metrics."
    ))

    s.append(Paragraph("9.2&nbsp;&nbsp;Lifecycle curation", H2))
    s.append(para(
        "Two commands handle explicit curation. <font name='Courier'>cma archive</font>"
        " moves cold notes into <font name='Courier'>vault/011-archive/</font> and "
        "sets their frontmatter <font name='Courier'>status: archived</font>. The "
        "cold-ness criterion is staged: last-retrieval timestamp from the retrieval "
        "log, falling back to the <font name='Courier'>created</font> frontmatter "
        "field, falling back to skip if neither signal is available. Filters by "
        "<font name='Courier'>--type</font>, <font name='Courier'>--status</font>, "
        "and <font name='Courier'>--older-than</font> days are composable."
    ))
    s.append(para(
        "<font name='Courier'>cma supersede &quot;Old&quot; --by &quot;New&quot;</font>"
        " marks a decision as superseded by another. It updates the old note's "
        "frontmatter (<font name='Courier'>status: superseded</font>, "
        "<font name='Courier'>superseded_by</font>, <font name='Courier'>superseded_at</font>)"
        " and appends a <font name='Courier'>**Superseded by [[New]].**</font> "
        "marker to the body. The wikilink ensures the supersedure is graph-visible: "
        "future retrievals reach the superseding note via the link, even when "
        "matching the old note by query."
    ))

    s.append(Paragraph("9.3&nbsp;&nbsp;Scaling characteristics", H2))
    s.append(para(
        "Table 2 reports per-vault size projections on commodity hardware "
        "(MiniLM-L6-v2 embeddings, 384 dimensions, single-CPU NumPy matmul, no "
        "ANN structures)."
    ))
    s.extend(make_table(
        ["Vault size", "Markdown", "Embeddings", "RAM", "Query latency"],
        [
            ["1K notes",   "~10 MB",  "~1.5 MB",   "~50 MB",   "&lt;50 ms"],
            ["10K notes",  "~100 MB", "~15 MB",    "~250 MB",  "&lt;100 ms"],
            ["100K notes", "~1 GB",   "~150 MB",   "~1.5 GB",  "~500 ms"],
            ["1M notes",   "~10 GB",  "~1.5 GB",   "~10+ GB",  "seconds; needs ANN"],
        ],
        col_widths=[1.0 * inch, 0.95 * inch, 1.05 * inch, 0.95 * inch, 1.5 * inch],
        caption="Table 2. Projected per-vault footprint and retrieval latency on "
                "commodity hardware. The reference Retriever uses a flat NumPy matrix "
                "for cosine similarity; beyond ~100K notes, an approximate-nearest-"
                "neighbor structure (FAISS, hnswlib) becomes preferable. Beyond "
                "~500K notes, sharding by domain or archiving cold notes is the "
                "preferred response.",
    ))

    # ---------- 10. ADRs ----------
    s.append(Paragraph("10.&nbsp;&nbsp;Architectural Decisions", H1))
    s.append(para(
        "We document five architectural decisions whose rationale is not obvious "
        "from the code."
    ))

    s.append(Paragraph("10.1&nbsp;&nbsp;BM25L over BM25Okapi and BM25Plus", H2))
    s.append(para(
        "Initial implementation used BM25Okapi. Its IDF formula, log( (N &minus; df + 0.5) / "
        "(df + 0.5) ), goes negative for df &gt; N/2. In wikilink-rich corpora, "
        "anchor text duplication causes common terms (e.g., domain vocabulary) to "
        "appear in many notes, producing negative IDF and pathological scoring "
        "behavior - all candidate documents end up scoring within a narrow band, "
        "destroying discrimination. BM25Plus avoids the negative IDF by introducing "
        "a delta term that gives every doc a baseline score, but this baseline "
        "interfered with our threshold-based filtering (every doc passed). BM25L's "
        "IDF, log( (N + 1) / (df + 0.5) ), is strictly positive and its TF "
        "saturation produces zero score for documents with no query terms. This is "
        "the correct shape for graph-derived corpora."
    ))

    s.append(Paragraph("10.2&nbsp;&nbsp;Seed threshold versus traversal threshold", H2))
    s.append(para(
        "The whitepaper drafts (v0.1, v0.2) listed <i>node_threshold</i> as a final "
        "filter applied uniformly to all candidates. In practice, this defeats "
        "GraphRAG: a pattern note linked from a strong seed almost never has direct "
        "lexical or semantic overlap with the query (its earned its place via the "
        "wikilink, not via the text). Filtering it produced retrieval indistinguishable "
        "from vector RAG. We resolved by gating <i>node_threshold</i> on seed "
        "selection only. Traversed nodes are admitted within the depth and beam "
        "budgets without further threshold filtering. Beam pruning is the volume "
        "control for traversed nodes; the threshold is the quality bar for direct hits."
    ))

    s.append(Paragraph("10.3&nbsp;&nbsp;Title repetition for BM25", H2))
    s.append(para(
        "Title tokens carry stronger signal than body tokens for retrieval. A "
        "principled solution is field-weighted BM25 (BM25F) with separate IDF "
        "tables per field; we instead concatenate the title three times before the "
        "body during tokenization. This is one parameter (the repetition count) "
        "rather than a separate index, integrates cleanly with rank_bm25's "
        "single-corpus API, and produces empirically similar ranking improvements "
        "on our test vaults. We may revisit if title-vs-body weighting becomes a "
        "performance bottleneck."
    ))

    s.append(Paragraph("10.4&nbsp;&nbsp;Vault canonicality", H2))
    s.append(para(
        "Memory must survive index corruption, version upgrades, and tool changes. "
        "Markdown with YAML frontmatter and wikilinks is the spec. Embeddings, BM25 "
        "pickles, graph JSON, and retrieval logs all live under "
        "<font name='Courier'>.cma/</font> and can be wiped + rebuilt by "
        "<font name='Courier'>cma index</font>. The Recorder is architecturally "
        "forbidden from writing to <font name='Courier'>.cma/</font>. This invariant "
        "is the basis of our portability and durability guarantees."
    ))

    s.append(Paragraph("10.5&nbsp;&nbsp;Per-agent topology", H2))
    s.append(para(
        "Default to one vault per agent. No shared global brain. This trades "
        "sub-linear scaling of memory size (each agent's vault is bounded) for "
        "the absence of automatic cross-agent learning. We argue the trade is "
        "correct: cross-agent leakage of decisions and patterns is a privacy and "
        "correctness hazard. The fractal layer (Section 7.2) provides explicit, "
        "controllable cross-agent retrieval when desired."
    ))

    # ---------- 11. limitations ----------
    s.append(Paragraph("11.&nbsp;&nbsp;Limitations and Future Work", H1))
    s.append(para(
        "The reference implementation has known limitations. Embedding inference is "
        "single-threaded NumPy matmul; for vaults beyond approximately 100K notes an "
        "approximate-nearest-neighbor structure such as FAISS or hnswlib becomes "
        "required. Wikilink resolution is title-or-stem case-insensitive matching "
        "without alias support; ambiguous links (two notes sharing a title) resolve "
        "non-deterministically. The MCP server exposes stdio transport only; an "
        "HTTP+SSE transport for hosted deployments is roadmap. The Recorder's "
        "duplicate detection is title-based and conservative; a content-similarity "
        "based check is future work."
    ))
    s.append(para(
        "Beyond these implementation gaps, several architectural extensions are on "
        "the roadmap: cluster consolidation via Leiden clustering with LLM-summarized "
        "cluster nodes prepended to specs; vault sharding with federated retrieval "
        "for vaults exceeding scaling thresholds; optional age-based decay scoring "
        "as a metadata boost; first-class typed edges (caused-by, supersedes, "
        "depends-on) with type-aware scoring; explicit memory provenance enforcement; "
        "and the cross-agent fractal layer."
    ))

    # ---------- references ----------
    s.append(Paragraph("References", H1))
    s.append(hrule())
    refs = [
        "[1] Lewis, P., Perez, E., Piktus, A., et al. (2020). "
        "<i>Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.</i> "
        "Advances in Neural Information Processing Systems.",

        "[2] Edge, D., Trinh, H., Cheng, N., et al. (2024). "
        "<i>From Local to Global: A Graph RAG Approach to Query-Focused "
        "Summarization.</i> arXiv:2404.16130.",

        "[3] Robertson, S. and Zaragoza, H. (2009). "
        "<i>The Probabilistic Relevance Framework: BM25 and Beyond.</i> "
        "Foundations and Trends in Information Retrieval, 3(4):333-389.",

        "[4] Lv, Y. and Zhai, C. (2011). <i>When documents are very long, BM25 "
        "fails!</i> Proceedings of the 34th International ACM SIGIR Conference, "
        "pp. 1103-1104.",

        "[5] Reimers, N. and Gurevych, I. (2019). <i>Sentence-BERT: Sentence "
        "Embeddings using Siamese BERT-Networks.</i> Proceedings of the 2019 "
        "Conference on Empirical Methods in Natural Language Processing.",

        "[6] Anthropic (2024). <i>Model Context Protocol Specification.</i> "
        "modelcontextprotocol.io.",

        "[7] Traag, V. A., Waltman, L., and van Eck, N. J. (2019). <i>From Louvain "
        "to Leiden: guaranteeing well-connected communities.</i> Scientific Reports, "
        "9(1):5233.",
    ]
    for r in refs:
        s.append(Paragraph(r, ParagraphStyle(
            "Ref", parent=BODY, leftIndent=18, firstLineIndent=-18,
            fontSize=9.5, leading=12, spaceAfter=4, alignment=TA_LEFT,
        )))

    # ---------- appendix A: configuration ----------
    s.append(section_break())
    s.append(Paragraph("Appendix A.&nbsp;&nbsp;Configuration Reference", H1))
    s.append(hrule())
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
        "  max_depth: 2                      # graph traversal hops\n"
        "  beam_width: 5                     # candidates kept per depth\n"
        "  node_threshold: 0.30              # SEED score floor only\n"
        "  fragment_threshold: 0.42          # paragraph score floor (depth > 0 only)\n"
        "  depth_decay: 0.80                 # final_score *= decay**depth\n"
        "  max_fragments_per_node: 3\n"
        "\n"
        "recorder:\n"
        "  require_human_approval_for:\n"
        "    - autonomy_change\n"
        "    - low_confidence_pattern\n"
        "    - supersede_decision\n"
        "  default_confidence: 0.60"
    ))

    # ---------- appendix B: CLI ----------
    s.append(Paragraph("Appendix B.&nbsp;&nbsp;CLI Reference", H1))
    s.append(hrule())
    s.extend(make_table(
        ["Command", "Description"],
        [
            ["cma add [path] [--user]",                      "One-shot: scaffold + wire prompt, sub-agents, MCP (&sect;7.3)."],
            ["cma init <path>",                              "Scaffold a new project (vault + config only). Used internally by cma add."],
            ["cma setup [path]",                             "Interactive: integration + embedding provider."],
            ["cma index [path] [--no-embeddings]",           "Training phase: parse, build graph, BM25, embeddings."],
            ["cma graph health [path]",                      "Graph structure report."],
            ["cma retrieve \"<query>\" [...]",               "Run Retriever, emit Context Spec, show context budget."],
            ["cma record <package.yaml> [--dry-run]",        "Recorder ingestion."],
            ["cma evals run <bench.yaml> [--mode M]",        "Benchmark suite runner."],
            ["cma mcp serve [--project p]",                  "Start MCP server over stdio."],
            ["cma health [--json]",                          "Memory health report."],
            ["cma archive [--type T] [--older-than D]",      "Archive cold notes."],
            ["cma supersede \"Old\" --by \"New\"",           "Mark old as superseded."],
            ["cma version",                                  "Print installed version."],
        ],
    ))

    # ---------- appendix C: MCP tools ----------
    s.append(Paragraph("Appendix C.&nbsp;&nbsp;MCP Tool Specifications", H1))
    s.append(hrule())
    s.extend(make_table(
        ["Tool", "Signature", "Purpose"],
        [
            ["search_notes",          "(query, top_k=5) -> [{title, type, score, ...}]",   "Hybrid lex+sem search."],
            ["get_note",              "(title) -> {title, body, frontmatter, links} | None", "Fetch a single note."],
            ["get_outgoing_links",    "(title) -> [title]",                                  "Forward wikilink targets."],
            ["get_backlinks",         "(title) -> [title]",                                  "Reverse wikilink sources."],
            ["traverse_graph",        "(start, depth=2) -> [{title, depth, type}]",         "BFS within N hops."],
            ["search_by_frontmatter", "(key, value) -> [{title, type, value}]",             "Metadata filter."],
            ["retrieve",              "(query, max_depth, beam_width) -> markdown",          "Full pipeline."],
            ["record_completion",     "(yaml_str, dry_run) -> {written, proposed, skipped}", "Recorder ingestion."],
            ["graph_health",          "() -> {nodes, edges, orphans, broken_links, ...}",    "Structure report."],
            ["reindex",               "() -> {status, n_records, n_edges}",                  "Rebuild in-memory state."],
        ],
        col_widths=[1.3 * inch, 2.5 * inch, 2.5 * inch],
    ))

    # ---------- end matter ----------
    s.append(Spacer(1, 0.3 * inch))
    s.append(HRFlowable(width="30%", thickness=0.4, color=INK,
                        spaceBefore=8, spaceAfter=8, hAlign="CENTER"))
    s.append(Paragraph(
        "End of paper. Contextual Memory Architecture, v0.5. "
        "github.com/danny-watkins/contextual-memory-architecture",
        ParagraphStyle("End", parent=BODY, alignment=TA_CENTER,
                       fontName="Times-Italic", textColor=DIM,
                       fontSize=9, leading=12),
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

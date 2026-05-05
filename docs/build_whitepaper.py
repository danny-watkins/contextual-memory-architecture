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

OUT = Path(__file__).parent / "CMA_Whitepaper_v0.4.pdf"
VERSION = "0.4"
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

    # ---------- 6. local-first substrate ----------
    s.append(Paragraph("6.&nbsp;&nbsp;Local-First Substrate", H1))
    s.append(Paragraph("6.1&nbsp;&nbsp;Vault layout", H2))
    s.append(para(
        "Each CMA project is a directory containing a single configuration file, a "
        "vault subdirectory (the canonical memory store), per-node working "
        "directories for Reasoner, Retriever, and Recorder artifacts, and a "
        "<font name='Courier'>.cma/</font> directory for derived state. The vault is "
        "organized into thirteen numbered subfolders (<font name='Courier'>000-inbox</font>"
        " through <font name='Courier'>011-archive</font>) corresponding to canonical "
        "note types: inbox, projects, sessions, decisions, patterns, people, tools, "
        "codebase, context-specs, evals, daily-log, archive. The numeric prefixes "
        "preserve sort order in any file browser and in Obsidian."
    ))

    s.append(Paragraph("6.2&nbsp;&nbsp;Derived state", H2))
    s.append(para(
        "<font name='Courier'>.cma/</font> contains the BM25 pickle, the embedding "
        "matrix as a NumPy <font name='Courier'>.npy</font> file with associated "
        "<font name='Courier'>doc_ids.json</font> and <font name='Courier'>meta.json</font>, "
        "the graph node manifest as JSON, the retrieval log as JSONL, and various "
        "caches and evaluation artifacts. Every artifact is regenerable from the "
        "vault by running <font name='Courier'>cma index</font>. This invariant - "
        "<i>vault is canonical, .cma/ is derived</i> - is enforced architecturally: "
        "the Recorder writes only to the vault, never to "
        "<font name='Courier'>.cma/</font>."
    ))

    s.append(Paragraph("6.3&nbsp;&nbsp;Portability", H2))
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
            ["cma init <path>",                              "Scaffold a new project."],
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
        "End of paper. Contextual Memory Architecture, v0.4. "
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

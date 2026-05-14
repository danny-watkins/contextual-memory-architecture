"""Command-line interface for CMA."""

from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import typer
import yaml
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from cma import __version__
from cma.activity import log_activity, read_events, render_dashboard_html
from cma.config import CMAConfig
from cma.health import health_report
from cma.ingest import DEFAULT_SOURCE_EXTENSIONS, ingest_sources
from cma.lifecycle import archive_cold_notes, supersede_decision
from cma.recorder import Recorder
from cma.retriever import EmbedderUnavailable, Retriever, get_embedder, render_markdown
from cma.retriever.embeddings import EmbeddingIndex
from cma.retriever.lexical import BM25Index
from cma.storage.graph_store import build_graph, graph_health_report
from cma.storage.markdown_store import parse_vault

app = typer.Typer(
    name="cma",
    help="Contextual Memory Architecture - a local-first memory layer for AI agents.",
    no_args_is_help=True,
    add_completion=False,
)
graph_app = typer.Typer(name="graph", help="Graph maintenance commands.", no_args_is_help=True)
app.add_typer(graph_app, name="graph")
console = Console()

VAULT_FOLDERS = [
    "000-inbox",
    "001-projects",
    "002-sessions",
    "003-decisions",
    "004-patterns",
    "005-people",
    "006-tools",
    "007-codebase",
    "008-context-specs",
    "009-evals",
    "010-daily-log",
    "011-archive",
    "020-sources",
    "020-substrate",
    "030-concepts",
    "040-technologies",
    "050-hubs",
]

# Operational logs and proposals live under cma/memory_log/, alongside the dashboard.
# The reasoner/recorder/retriever role-specific working dirs from earlier whitepaper
# iterations are gone -- the host agent IS the Reasoner, and what the Retriever and
# Recorder actually write all goes to either the vault or memory_log/.
MEMORY_LOG_FOLDERS = ["write_logs", "proposals"]

DERIVED_FOLDERS = ["graph", "embeddings", "bm25", "cache", "state", "eval_runs"]

DEFAULT_CONFIG = """\
# Contextual Memory Architecture configuration
# All CMA-managed paths live under ./cma/ to keep your project root clean.
vault_path: ./cma/vault
index_path: ./cma/cache

# Embedding provider for the Retriever's semantic search.
# Options:
#   sentence-transformers  - local, no API key (default; install: pip install 'cma[embeddings]')
#   openai                 - OpenAI embeddings (install: pip install 'cma[openai]'; needs OPENAI_API_KEY)
#   none                   - BM25 lexical search only, no embeddings
embedding_provider: sentence-transformers
embedding_model: all-MiniLM-L6-v2

retrieval:
  alpha: 0.7
  max_depth: 2
  beam_width: 5
  node_threshold: 0.30
  fragment_threshold: 0.42
  depth_decay: 0.80
  max_fragments_per_node: 3

recorder:
  require_human_approval_for:
    - autonomy_change
    - low_confidence_pattern
    - supersede_decision
  default_confidence: 0.60
"""

WELCOME_NOTE = """\
---
type: note
title: Welcome
tags: [getting-started]
status: active
---

# Welcome to your CMA vault

This vault is the canonical memory store for your agent.

Drop markdown notes anywhere under `cma/vault/` and link them using
Obsidian-style wiki links (double square brackets around a note title).
Add YAML frontmatter at the top of any note to attach metadata: type,
status, confidence, tags, domain.

When you run `cma index`, the system parses every note, extracts
frontmatter, follows links, and builds a graph. Then run `cma graph health`
to inspect the structure.

Next: read [[Quickstart]].
"""

QUICKSTART_NOTE = """\
---
type: note
title: Quickstart
tags: [getting-started]
status: active
---

# Quickstart

1. Add notes anywhere under the vault folder
2. Link them using double-bracket wiki syntax around a note title
3. Add YAML frontmatter for metadata
4. Run `cma index` to parse the vault and build the graph
5. Run `cma graph health` for a structure report

Back to [[Welcome]].
"""


def _load_config(project_path: Path) -> CMAConfig:
    return CMAConfig.from_project(project_path).resolve_paths(project_path)


@app.command()
def version() -> None:
    """Print the installed CMA version."""
    console.print(f"cma {__version__}")


def _scaffold_project(project_path: Path, force: bool = False) -> Path:
    """Create vault, node folders, and default config under <project_path>/cma/.

    Layout (everything CMA-related lives under ./cma/ to keep the agent's root clean):
        <project>/cma/config.yaml
        <project>/cma/vault/<folder>/
        <project>/cma/{reasoner,recorder,retriever}/<sub>/
        <project>/cma/cache/<sub>/
    """
    project_path = Path(project_path).resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    cma_root = project_path / "cma"
    cma_root.mkdir(exist_ok=True)

    config_file = cma_root / "config.yaml"
    if config_file.exists() and not force:
        return project_path

    config_file.write_text(DEFAULT_CONFIG, encoding="utf-8")

    for folder in VAULT_FOLDERS:
        (cma_root / "vault" / folder).mkdir(parents=True, exist_ok=True)

    for sub in DERIVED_FOLDERS:
        (cma_root / "cache" / sub).mkdir(parents=True, exist_ok=True)

    for sub in MEMORY_LOG_FOLDERS:
        (cma_root / "memory_log" / sub).mkdir(parents=True, exist_ok=True)

    welcome_path = cma_root / "vault" / "000-inbox" / "Welcome.md"
    quickstart_path = cma_root / "vault" / "000-inbox" / "Quickstart.md"
    if not welcome_path.exists():
        welcome_path.write_text(WELCOME_NOTE, encoding="utf-8")
    if not quickstart_path.exists():
        quickstart_path.write_text(QUICKSTART_NOTE, encoding="utf-8")

    # Copy the bundled .obsidian/ config into the new vault so the graph view
    # picks up the heatmap color groups and context_spec/cma_active highlights
    # on first open. User-specific files (workspace.json) are not bundled.
    import shutil
    obsidian_src = _bundle_root() / "obsidian"
    obsidian_dest = cma_root / "vault" / ".obsidian"
    if obsidian_src.exists() and not obsidian_dest.exists():
        obsidian_dest.mkdir(parents=True)
        for src in obsidian_src.glob("*.json"):
            shutil.copy2(src, obsidian_dest / src.name)

    # Initialize the memory_log/ dashboard so opening it shows an empty-state
    # message before the first event lands. The write_logs/ and proposals/ subdirs
    # were already created above.
    initial_html = render_dashboard_html([], project_path)
    (cma_root / "memory_log" / "dashboard.html").write_text(initial_html, encoding="utf-8")

    return project_path


@app.command()
def init(
    project_path: Path = typer.Argument(..., help="Path to create the CMA project at."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite an existing config."),
) -> None:
    """Initialize a new CMA project with vault, node folders, and default config."""
    project_path = Path(project_path).resolve()
    config_file = project_path / "cma/config.yaml"
    if config_file.exists() and not force:
        console.print(
            f"[yellow]Config already exists at {config_file}. "
            "Use --force to overwrite.[/yellow]"
        )
        raise typer.Exit(code=1)

    project_path = _scaffold_project(project_path, force=force)

    console.print(
        Panel.fit(
            f"[green]Initialized CMA project at[/green] [bold]{project_path}[/bold]\n\n"
            "Next steps:\n"
            f"  [cyan]cd {project_path.name}[/cyan]\n"
            "  [cyan]cma add[/cyan]              # wire CMA into Claude Code (CLAUDE.md, agents, MCP)\n"
            "  [cyan]cma setup[/cyan]            # configure your LLM/agent integration\n"
            "  [cyan]cma index[/cyan]            # train the memory graph\n\n"
            "[dim]Tip: in a fresh directory, [cyan]cma add[/cyan] alone does init + wiring in one step.[/dim]",
            title="CMA",
            border_style="green",
        )
    )


def _run_index_build(project_path: Path, no_embeddings: bool = False) -> None:
    """Body of the index command, callable as a function from elsewhere (e.g., `cma add`)."""
    import time as _time
    started = _time.perf_counter()
    config = _load_config(project_path)
    vault_path = Path(config.vault_path)

    if not vault_path.exists():
        console.print(f"[red]Vault not found at {vault_path}. Run `cma add` first.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[dim]Parsing vault at {vault_path}...[/dim]")
    records = parse_vault(vault_path)
    console.print(f"[green]Parsed {len(records)} notes.[/green]")

    g = build_graph(records)
    console.print(
        f"[green]Built graph: {g.number_of_nodes()} nodes, "
        f"{g.number_of_edges()} edges.[/green]"
    )

    index_root = Path(config.index_path)
    graph_dir = index_root / "graph"
    bm25_dir = index_root / "bm25"
    emb_dir = index_root / "embeddings"
    for d in (graph_dir, bm25_dir, emb_dir):
        d.mkdir(parents=True, exist_ok=True)

    manifest = [
        {
            "record_id": r.record_id,
            "type": r.type,
            "title": r.title,
            "path": r.path,
            "tags": r.tags,
            "links": r.links,
            "status": r.status,
        }
        for r in records
    ]
    (graph_dir / "nodes.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    console.print(f"[dim]Wrote node manifest -> {graph_dir / 'nodes.json'}[/dim]")

    bm25 = BM25Index(records)
    with open(bm25_dir / "index.pkl", "wb") as f:
        pickle.dump({"doc_ids": bm25.doc_ids, "tokenized": bm25._tokenized}, f)
    console.print(f"[dim]Wrote BM25 index -> {bm25_dir / 'index.pkl'}[/dim]")

    if no_embeddings or config.embedding_provider in ("none", ""):
        console.print(
            "[yellow]Skipping embeddings (provider=none or --no-embeddings).[/yellow]"
        )
    else:
        try:
            embedder = get_embedder(config.embedding_provider, config.embedding_model)
        except EmbedderUnavailable as e:
            console.print(f"[yellow]{e}[/yellow]")
            console.print("[yellow]Skipping embeddings.[/yellow]")
            embedder = None
        if embedder is not None:
            console.print(f"[dim]Computing embeddings with {embedder.name}...[/dim]")
            ei = EmbeddingIndex.build(records, embedder)
            np.save(emb_dir / "embeddings.npy", ei.matrix)
            (emb_dir / "doc_ids.json").write_text(
                json.dumps(ei.doc_ids, indent=2), encoding="utf-8"
            )
            (emb_dir / "meta.json").write_text(
                json.dumps(
                    {
                        "embedder": embedder.name,
                        "dim": embedder.dim,
                        "n_docs": len(ei.doc_ids),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            console.print(f"[green]Wrote embeddings ({len(ei.doc_ids)} x {embedder.dim}).[/green]")

    duration_ms = (_time.perf_counter() - started) * 1000
    log_activity(
        project_path, "index",
        duration_ms=duration_ms,
        summary=f"{len(records)} notes, {g.number_of_nodes()} nodes, {g.number_of_edges()} edges",
        details={
            "n_notes": len(records),
            "n_nodes": g.number_of_nodes(),
            "n_edges": g.number_of_edges(),
            "embeddings": not no_embeddings and config.embedding_provider not in ("none", ""),
        },
    )


@app.command()
def index(
    project_path: Path = typer.Argument(Path("."), help="Path to the CMA project."),
    no_embeddings: bool = typer.Option(
        False, "--no-embeddings", help="Skip embeddings (BM25 only)."
    ),
) -> None:
    """Parse the vault and build the memory graph + indexes (the training phase).

    Builds and persists:
      - cma/cache/graph/nodes.json      (node manifest)
      - cma/cache/bm25/index.pkl        (BM25 index)
      - cma/cache/embeddings/*.npy      (embeddings, if a provider is configured)
    """
    _run_index_build(Path(project_path).resolve(), no_embeddings=no_embeddings)


# -------- ingest --------


def _parse_extensions(value: str | None) -> set[str]:
    if not value:
        return set(DEFAULT_SOURCE_EXTENSIONS)
    parsed = set()
    for item in value.split(","):
        item = item.strip().lower()
        if not item:
            continue
        parsed.add(item if item.startswith(".") else f".{item}")
    return parsed or set(DEFAULT_SOURCE_EXTENSIONS)


@app.command("ingest-folder")
def ingest_folder(
    source_dir: Path = typer.Argument(..., help="Folder of project files to normalize."),
    project_path: Path = typer.Option(
        Path("."), "--project", "-p", help="Path to the CMA project."
    ),
    extensions: str = typer.Option(
        None,
        "--extensions",
        help="Comma-separated extensions to import, e.g. md,txt,py,json,yaml.",
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace existing imported notes."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
    max_bytes: int = typer.Option(
        200_000, "--max-bytes", help="Skip source files larger than this many bytes."
    ),
    max_chars: int = typer.Option(
        20_000, "--max-chars", help="Maximum characters copied into each source note."
    ),
    min_chars: int = typer.Option(
        20, "--min-chars", help="Skip files whose stripped content is shorter than this."
    ),
    exclude_glob: list[str] = typer.Option(
        None,
        "--exclude-glob",
        help="Skip files whose source-relative path matches this glob (repeatable).",
    ),
    index_after: bool = typer.Option(
        False, "--index", help="Run `cma index --no-embeddings` after ingesting."
    ),
) -> None:
    """Normalize a folder of source files into CMA/Obsidian markdown notes.

    Writes source notes under `vault/020-sources/<project>/` and project notes
    under `vault/001-projects/`. Run `cma index` afterwards to train the graph.
    """
    project_path = Path(project_path).resolve()
    if not (project_path / "cma/config.yaml").exists():
        console.print(f"[red]No cma/config.yaml at {project_path}. Run `cma init` first.[/red]")
        raise typer.Exit(code=1)

    result = ingest_sources(
        source_dir=Path(source_dir),
        project_path=project_path,
        extensions=_parse_extensions(extensions),
        exclude_globs=exclude_glob,
        overwrite=overwrite,
        dry_run=dry_run,
        max_bytes=max_bytes,
        max_chars=max_chars,
        min_chars=min_chars,
    )

    summary = Table(title="Ingest Folder Result", show_header=False, box=None)
    summary.add_row("Mode", "DRY RUN" if dry_run else "live")
    summary.add_row("Imported", str(len(result.imported)))
    summary.add_row("Skipped", str(len(result.skipped)))
    summary.add_row("Errors", str(len(result.errors)))
    console.print(summary)

    if result.imported:
        t = Table(title="Imported" if not dry_run else "Would Import")
        t.add_column("Path")
        for p in result.imported[:50]:
            t.add_row(str(p))
        console.print(t)
        if len(result.imported) > 50:
            console.print(f"[dim]...and {len(result.imported) - 50} more[/dim]")

    if result.skipped:
        t = Table(title="Skipped")
        t.add_column("Source")
        t.add_column("Reason")
        for source, reason in result.skipped[:50]:
            t.add_row(str(source), reason)
        console.print(t)
        if len(result.skipped) > 50:
            console.print(f"[dim]...and {len(result.skipped) - 50} more skipped[/dim]")

    if result.errors:
        t = Table(title="Errors")
        t.add_column("Source")
        t.add_column("Error")
        for source, error in result.errors[:50]:
            t.add_row(str(source), error)
        console.print(t)
        raise typer.Exit(code=1)

    if index_after and not dry_run:
        console.print("\n[dim]Indexing imported notes (BM25 + graph, no embeddings)...[/dim]")
        index(project_path, no_embeddings=True)
    elif not dry_run:
        console.print("\n[dim]Next: run `cma index --no-embeddings` to refresh the graph.[/dim]")


@app.command()
def retrieve(
    query: str = typer.Argument(..., help="Natural-language query."),
    project_path: Path = typer.Option(
        Path("."), "--project", "-p", help="Path to the CMA project."
    ),
    max_depth: int = typer.Option(None, "--max-depth", help="Override config max_depth."),
    beam_width: int = typer.Option(None, "--beam-width", help="Override config beam_width."),
    save: Path = typer.Option(
        None, "--save", help="Write the rendered context spec to this path."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Print the context spec as JSON instead of markdown."
    ),
    demo: bool = typer.Option(
        False,
        "--demo",
        help="Slow down the traversal so an open Obsidian graph view shows the agent walking node-by-node.",
    ),
    demo_step: float = typer.Option(
        0.8,
        "--demo-step",
        help="Seconds to pause on each node in --demo mode.",
    ),
) -> None:
    """Run the Retriever and emit a Context Spec for the query."""
    project_path = Path(project_path).resolve()
    retriever = Retriever.from_project(project_path)

    if demo:
        console.print(
            f"[dim]Demo mode: walking the graph at {demo_step}s per hop. "
            "Switch to your Obsidian graph view now.[/dim]\n"
        )

    spec = retriever.retrieve(
        query,
        max_depth=max_depth,
        beam_width=beam_width,
        demo=demo,
        demo_step_seconds=demo_step,
    )

    if json_output:
        out = spec.model_dump_json(indent=2)
        # rich.Console soft-wraps long lines, which would insert newlines inside
        # JSON string fields and corrupt the output. Plain `print` would also
        # fail on Windows when fragments contain non-cp1252 chars (e.g. unicode
        # arrows). Write UTF-8 bytes straight to stdout to dodge both.
        sys.stdout.buffer.write(out.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.flush()
    else:
        md = render_markdown(spec)
        console.print(Markdown(md))

    if save:
        save_path = Path(save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if json_output:
            save_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
        else:
            save_path.write_text(render_markdown(spec), encoding="utf-8")
        console.print(f"[dim]Saved context spec -> {save_path}[/dim]")

    # Context % gauge: how much of the configured token budget did this spec consume?
    # Skip in --json mode so stdout stays parseable. In markdown mode this is a
    # helpful interactive footer.
    if not json_output:
        config = CMAConfig.from_project(project_path)
        token_budget = 8000  # default - mirrors the ContextRequest schema default
        used_tokens = sum(len(f.text) for f in spec.fragments) // 4
        pct = (used_tokens / token_budget * 100) if token_budget else 0.0
        bar_width = 30
        filled = min(bar_width, int(pct / 100 * bar_width))
        bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
        color = "green" if pct < 60 else "yellow" if pct < 90 else "red"
        console.print(
            f"\n[bold]Context budget[/bold] {bar} "
            f"[{color}]{used_tokens:,} / {token_budget:,} tokens ({pct:.0f}%)[/{color}]  "
            f"| {len(spec.fragments)} fragments from {len({f.source_node for f in spec.fragments})} notes"
        )


# -------- setup helper --------


CLAUDE_CODE_MCP_SNIPPET = """\
# Claude Code MCP integration (Phase 6 - coming soon)
#
# When Phase 6 lands, you will register CMA as an MCP server in your Claude
# Code config so the agent can call retrieve() and record() as tools.
#
# Add to your Claude Code MCP config (~/.claude/mcp.json or project .mcp.json):
#
# {{
#   "mcpServers": {{
#     "cma": {{
#       "command": "cma",
#       "args": ["mcp", "serve", "--project", "{project_path}"]
#     }}
#   }}
# }}
#
# Until Phase 6 ships, integrate via the Python SDK or shell out to:
#   cma retrieve "<query>" --project {project_path}
"""


@app.command()
def setup(
    project_path: Path = typer.Argument(Path("."), help="Path to the CMA project."),
) -> None:
    """Interactive helper: configure agent integration + embedding provider."""
    project_path = Path(project_path).resolve()
    config_path = project_path / "cma/config.yaml"
    if not config_path.exists():
        console.print(
            f"[red]No cma/config.yaml at {project_path}. Run `cma init {project_path}` first.[/red]"
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "[bold]CMA setup[/bold]\n\n"
            "Two questions: how your agent will call CMA, and which embedder to use.",
            border_style="cyan",
        )
    )

    # 1. Agent integration
    console.print("\n[bold]1. How will your agent call CMA?[/bold]")
    console.print("  [cyan]1[/cyan]) Claude Code (via MCP)  [dim]- recommended for most users[/dim]")
    console.print("  [cyan]2[/cyan]) Python SDK             [dim]- import cma in your agent code[/dim]")
    console.print("  [cyan]3[/cyan]) Generic CLI            [dim]- shell out to `cma retrieve`[/dim]")
    integration = typer.prompt("Choice", default="1").strip()

    # 2. Embedding provider
    console.print("\n[bold]2. Embedding provider for semantic search?[/bold]")
    console.print(
        "  [cyan]1[/cyan]) sentence-transformers  "
        "[dim]- local, no API key, ~80MB model (default)[/dim]"
    )
    console.print(
        "  [cyan]2[/cyan]) openai                 "
        "[dim]- needs OPENAI_API_KEY in env[/dim]"
    )
    console.print(
        "  [cyan]3[/cyan]) none                   "
        "[dim]- BM25 lexical search only, no embeddings[/dim]"
    )
    embed_choice = typer.prompt("Choice", default="1").strip()

    embed_provider, embed_model = {
        "1": ("sentence-transformers", "all-MiniLM-L6-v2"),
        "2": ("openai", "text-embedding-3-small"),
        "3": ("none", ""),
    }.get(embed_choice, ("sentence-transformers", "all-MiniLM-L6-v2"))

    # Apply config changes
    with open(config_path, "r", encoding="utf-8") as f:
        cfg_data = yaml.safe_load(f) or {}
    cfg_data["embedding_provider"] = embed_provider
    cfg_data["embedding_model"] = embed_model
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg_data, f, sort_keys=False)
    console.print(f"\n[green]Updated[/green] {config_path}")

    # Print integration guidance
    console.print()
    if integration == "1":
        console.print(
            Panel(
                CLAUDE_CODE_MCP_SNIPPET.format(project_path=project_path),
                title="Claude Code integration",
                border_style="green",
            )
        )
    elif integration == "2":
        console.print(
            Panel(
                "from cma import Retriever\n\n"
                f"retriever = Retriever.from_project(r\"{project_path}\")\n"
                "spec = retriever.retrieve(\"your query here\")\n"
                "print(spec.fragments)",
                title="Python SDK integration",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"cma retrieve \"your query\" --project {project_path}\n"
                f"cma retrieve \"your query\" --project {project_path} --json",
                title="Generic CLI integration",
                border_style="green",
            )
        )

    # Embedding follow-up
    if embed_provider == "sentence-transformers":
        console.print(
            "\n[yellow]Install the embedding extra if you have not yet:[/yellow]"
        )
        console.print("  pip install 'contextual-memory-architecture[embeddings]'")
    elif embed_provider == "openai":
        console.print("\n[yellow]Make sure these are set:[/yellow]")
        console.print("  pip install 'contextual-memory-architecture[openai]'")
        if not os.environ.get("OPENAI_API_KEY"):
            console.print("  export OPENAI_API_KEY=sk-...   [dim](currently unset)[/dim]")
        else:
            console.print("  OPENAI_API_KEY is set.")

    console.print(
        "\n[bold]Next:[/bold] [cyan]cma index[/cyan] to train the memory graph."
    )


# -------- record --------


@app.command()
def record(
    completion_package: Path = typer.Argument(
        ..., help="Path to a completion package YAML or JSON file."
    ),
    project_path: Path = typer.Option(
        Path("."), "--project", "-p", help="Path to the CMA project."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be written without writing."
    ),
) -> None:
    """Ingest a completion package and write structured memory back to the vault."""
    project_path = Path(project_path).resolve()
    if not (project_path / "cma/config.yaml").exists():
        console.print(
            f"[red]No cma/config.yaml at {project_path}. Run `cma init` first.[/red]"
        )
        raise typer.Exit(code=1)

    package_path = Path(completion_package).resolve()
    if not package_path.exists():
        console.print(f"[red]Completion package not found: {package_path}[/red]")
        raise typer.Exit(code=1)

    recorder = Recorder.from_project(project_path)
    package = Recorder.load_completion_package(package_path)
    result = recorder.record_completion(package, dry_run=dry_run)

    summary = Table(title="Recorder Result", show_header=False, box=None)
    summary.add_row("Task ID", package.task_id)
    summary.add_row("Written", str(len(result.written)))
    summary.add_row("Proposed", str(len(result.proposed)))
    summary.add_row("Skipped", str(len(result.skipped)))
    summary.add_row("Mode", "DRY RUN" if dry_run else "live")
    console.print(summary)

    if result.written:
        t = Table(title="Written")
        t.add_column("Path")
        for p in result.written:
            t.add_row(str(p))
        console.print(t)

    if result.proposed:
        t = Table(title="Proposed (need human approval)")
        t.add_column("Path")
        for p in result.proposed:
            t.add_row(str(p))
        console.print(t)

    if result.skipped:
        t = Table(title="Skipped")
        t.add_column("Item")
        t.add_column("Reason")
        for label, reason in result.skipped:
            t.add_row(label, reason)
        console.print(t)

    if not dry_run and result.written:
        console.print(
            "\n[dim]Tip: run `cma index` to refresh BM25/embeddings so new notes are retrievable.[/dim]"
        )


# -------- graph commands --------


@graph_app.command("health")
def graph_health(
    project_path: Path = typer.Argument(Path("."), help="Path to the CMA project."),
) -> None:
    """Report graph structure: node counts by type, orphans, broken links."""
    project_path = Path(project_path).resolve()
    config = _load_config(project_path)
    vault_path = Path(config.vault_path)

    if not vault_path.exists():
        console.print(f"[red]Vault not found at {vault_path}. Run `cma init` first.[/red]")
        raise typer.Exit(code=1)

    records = parse_vault(vault_path)
    g = build_graph(records)
    report = graph_health_report(g)

    summary = Table(title="Graph Health", show_header=False, box=None)
    summary.add_row("Total notes", str(report["total_nodes"]))
    summary.add_row("Total edges", str(report["total_edges"]))
    summary.add_row("Missing link targets", str(report["missing_nodes"]))
    summary.add_row("Orphans", str(len(report["orphans"])))
    summary.add_row("Broken links", str(len(report["broken_links"])))
    console.print(summary)

    if report["node_types"]:
        types_table = Table(title="Notes by Type")
        types_table.add_column("Type")
        types_table.add_column("Count", justify="right")
        for t, c in sorted(report["node_types"].items(), key=lambda x: -x[1]):
            types_table.add_row(t, str(c))
        console.print(types_table)

    if report["orphans"]:
        orphan_table = Table(title="Orphan Notes (no incoming or outgoing existing links)")
        orphan_table.add_column("Note")
        for n in report["orphans"][:50]:
            orphan_table.add_row(n)
        console.print(orphan_table)

    if report["broken_links"]:
        broken_table = Table(title="Broken Wikilinks")
        broken_table.add_column("Source")
        broken_table.add_column("Target (missing)")
        for bl in report["broken_links"][:50]:
            broken_table.add_row(bl["source"], bl["target"])
        console.print(broken_table)


# -------- health --------


def _format_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


@app.command()
def health(
    project_path: Path = typer.Argument(Path("."), help="Path to the CMA project."),
    json_output: bool = typer.Option(False, "--json", help="Print the report as JSON."),
) -> None:
    """Memory health report: vault size, index footprint, graph density, retrieval activity."""
    project_path = Path(project_path).resolve()
    if not (project_path / "cma/config.yaml").exists():
        console.print(f"[red]No cma/config.yaml at {project_path}.[/red]")
        raise typer.Exit(code=1)

    report = health_report(project_path)

    if json_output:
        console.print(json.dumps(report, indent=2, default=str))
        return

    # Vault
    v = report["vault"]
    vault_table = Table(title="Vault", show_header=False, box=None)
    vault_table.add_row("Total notes", f"{v['total_notes']:,}")
    vault_table.add_row("Total size", _format_bytes(v["total_bytes"]))
    console.print(vault_table)

    if v["by_folder"]:
        bf = Table(title="By Folder", show_header=True)
        bf.add_column("Folder")
        bf.add_column("Notes", justify="right")
        bf.add_column("Size", justify="right")
        for folder, stats in v["by_folder"].items():
            bf.add_row(folder, str(stats["notes"]), _format_bytes(stats["bytes"]))
        console.print(bf)

    # Indexes
    idx = report["indexes"]
    idx_table = Table(title="Indexes (.cma/)", show_header=True)
    idx_table.add_column("Index")
    idx_table.add_column("Size", justify="right")
    idx_table.add_column("Detail")
    idx_table.add_row("graph", _format_bytes(idx["graph"]["bytes"]), "")
    idx_table.add_row("bm25", _format_bytes(idx["bm25"]["bytes"]), "")
    emb = idx["embeddings"]
    emb_detail = (
        f"{emb['n_docs']} docs x {emb['dim']} dims ({emb['model']})"
        if emb["n_docs"]
        else "(not built)"
    )
    idx_table.add_row("embeddings", _format_bytes(emb["bytes"]), emb_detail)
    idx_table.add_row("[bold]total derived[/bold]", _format_bytes(idx["total_derived_bytes"]), "")
    console.print(idx_table)

    # Graph
    g = report["graph"]
    g_table = Table(title="Graph", show_header=False, box=None)
    g_table.add_row("Nodes", str(g["total_nodes"]))
    g_table.add_row("Edges", str(g["total_edges"]))
    g_table.add_row("Avg out-degree", f"{g['average_out_degree']:.2f}")
    g_table.add_row("Orphans", f"{g['orphans']} ({g['orphan_rate']:.1%})")
    g_table.add_row("Broken links", f"{g['broken_links']} ({g['broken_link_rate']:.1%})")
    console.print(g_table)

    # Retrieval
    r = report["retrieval"]
    r_table = Table(title="Retrieval Activity", show_header=False, box=None)
    r_table.add_row("Total events", str(r["total_events"]))
    r_table.add_row("Last 7 days", str(r["events_last_7d"]))
    r_table.add_row("Never retrieved", f"{r['never_retrieved']} ({r['never_retrieved_rate']:.1%})")
    console.print(r_table)

    if r["most_retrieved"]:
        mr = Table(title="Most Retrieved", show_header=True)
        mr.add_column("Note")
        mr.add_column("Hits", justify="right")
        for note, hits in r["most_retrieved"]:
            mr.add_row(str(note), str(hits))
        console.print(mr)

    # Warnings
    if report["warnings"]:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for w in report["warnings"]:
            console.print(f"  [yellow]![/yellow] {w}")
    else:
        console.print("\n[green]All metrics within healthy thresholds.[/green]")


# -------- archive / supersede --------


@app.command()
def archive(
    older_than: int = typer.Option(
        None, "--older-than", help="Archive notes whose last activity is older than N days."
    ),
    note_type: str = typer.Option(None, "--type", help="Only archive notes of this type."),
    only_status: str = typer.Option(
        None, "--status", help="Only archive notes with this status."
    ),
    project_path: Path = typer.Option(Path("."), "--project", "-p"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without moving files."),
) -> None:
    """Move cold notes into vault/011-archive/ and mark them archived."""
    project_path = Path(project_path).resolve()
    if not (project_path / "cma/config.yaml").exists():
        console.print(f"[red]No cma/config.yaml at {project_path}.[/red]")
        raise typer.Exit(code=1)

    if older_than is None and note_type is None and only_status is None:
        console.print(
            "[red]Refusing to archive everything.[/red] "
            "Specify at least one filter: --older-than, --type, or --status."
        )
        raise typer.Exit(code=2)

    result = archive_cold_notes(
        project_path,
        older_than_days=older_than,
        note_type=note_type,
        only_status=only_status,
        dry_run=dry_run,
    )

    summary = Table(title="Archive Result", show_header=False, box=None)
    summary.add_row("Mode", "DRY RUN" if dry_run else "live")
    summary.add_row("Moved", str(len(result.moved)))
    summary.add_row("Skipped", str(len(result.skipped)))
    console.print(summary)

    if result.moved:
        t = Table(title="Moved" if not dry_run else "Would move")
        t.add_column("From")
        t.add_column("To")
        for src, dst in result.moved:
            t.add_row(str(src), str(dst))
        console.print(t)

    if result.skipped:
        t = Table(title="Skipped")
        t.add_column("Note")
        t.add_column("Reason")
        for note, reason in result.skipped:
            t.add_row(note, reason)
        console.print(t)


@app.command()
def supersede(
    old_title: str = typer.Argument(..., help="Title of the note being superseded."),
    by: str = typer.Option(..., "--by", help="Title of the note that supersedes it."),
    project_path: Path = typer.Option(Path("."), "--project", "-p"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Mark a decision as superseded by a newer one (updates frontmatter + adds wikilink)."""
    project_path = Path(project_path).resolve()
    if not (project_path / "cma/config.yaml").exists():
        console.print(f"[red]No cma/config.yaml at {project_path}.[/red]")
        raise typer.Exit(code=1)

    try:
        path = supersede_decision(project_path, old_title, by, dry_run=dry_run)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    if dry_run:
        console.print(f"[yellow]DRY RUN[/yellow]: would supersede [bold]{old_title}[/bold] by [bold]{by}[/bold]")
    else:
        console.print(f"[green]Superseded[/green] [bold]{old_title}[/bold] -> [bold]{by}[/bold]\n[dim]Updated: {path}[/dim]")


# -------- evals --------

evals_app = typer.Typer(
    name="evals", help="Run benchmark queries against the CMA project.", no_args_is_help=True
)
app.add_typer(evals_app, name="evals")


@evals_app.command("run")
def evals_run(
    benchmark: Path = typer.Argument(..., help="Path to a benchmark YAML/JSON file."),
    project_path: Path = typer.Option(Path("."), "--project", "-p"),
    mode: str = typer.Option(
        "graphrag",
        "--mode",
        help="Retrieval mode: no_memory | vector_only | graphrag | full_cma",
    ),
    save: Path = typer.Option(None, "--save", help="Write the run report as JSON."),
) -> None:
    """Run a benchmark suite and report retrieval-quality metrics."""
    from cma.evals import RetrievalMode
    from cma.evals.runner import load_benchmark_queries, run_benchmark

    project_path = Path(project_path).resolve()
    queries = load_benchmark_queries(Path(benchmark))
    try:
        retrieval_mode = RetrievalMode(mode)
    except ValueError:
        console.print(f"[red]Unknown mode: {mode}[/red]")
        raise typer.Exit(code=2)

    run = run_benchmark(project_path, queries, mode=retrieval_mode)
    agg = run.aggregate()

    summary = Table(title=f"Benchmark Run ({mode})", show_header=False, box=None)
    for k, v in agg.items():
        summary.add_row(k, f"{v:.4f}" if isinstance(v, float) else str(v))
    console.print(summary)

    if save:
        save_path = Path(save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": run.mode.value,
            "project_path": str(run.project_path),
            "started_at": run.started_at.isoformat(),
            "aggregate": agg,
            "results": [
                {
                    "query": r.query,
                    "retrieved": r.retrieved_record_ids,
                    "expected": r.expected_record_ids,
                    "recall_at_5": r.recall_at_5,
                    "precision_at_5": r.precision_at_5,
                    "n_fragments": r.n_fragments,
                    "n_unique_sources": r.n_unique_sources,
                    "token_estimate": r.raw_spec_token_estimate,
                }
                for r in run.results
            ],
        }
        save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[dim]Saved benchmark report -> {save_path}[/dim]")


# -------- mcp server --------

mcp_app = typer.Typer(name="mcp", help="MCP server for agent integration.", no_args_is_help=True)
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("serve")
def mcp_serve(
    project_path: Path = typer.Option(
        Path("."), "--project", "-p", help="Path to the CMA project."
    ),
) -> None:
    """Start the CMA MCP server over stdio.

    Use with Claude Code by adding to your MCP config (~/.claude/mcp.json):

        {
          "mcpServers": {
            "cma": {
              "command": "cma",
              "args": ["mcp", "serve", "--project", "/path/to/project"]
            }
          }
        }

    Requires: pip install 'contextual-memory-architecture[mcp]'
    """
    project_path = Path(project_path).resolve()
    if not (project_path / "cma/config.yaml").exists():
        # Status messages must go to stderr so they don't corrupt the stdio JSON-RPC stream.
        print(f"[red]No cma/config.yaml at {project_path}.[/red]", file=sys.stderr)
        raise typer.Exit(code=1)

    try:
        from cma.mcp.server import run_server
    except ImportError as e:
        print(
            f"[red]MCP support not installed:[/red] {e}\n"
            "Install with: pip install 'contextual-memory-architecture[mcp]'",
            file=sys.stderr,
        )
        raise typer.Exit(code=1)

    run_server(project_path)


# -------- cma add (one-shot install) --------

_BUNDLE_BEGIN = "<!-- BEGIN CMA AGENT PROMPT -->"
_BUNDLE_END = "<!-- END CMA AGENT PROMPT -->"


def _bundle_root() -> Path:
    """Locate the shipped bundle directory inside the installed package."""
    return Path(__file__).parent / "_bundle"


def _render_prompt(project_path: Path) -> str:
    """Read AGENT_PROMPT.md and substitute {{VAULT_PATH}} with the resolved vault path
    inside the project's ./cma/ folder."""
    prompt_src = _bundle_root() / "prompts" / "AGENT_PROMPT.md"
    text = prompt_src.read_text(encoding="utf-8")
    vault_path = project_path / "cma" / "vault"
    return text.replace("{{VAULT_PATH}}", str(vault_path))


def _write_claude_md(target: Path, prompt_text: str) -> str:
    """Write or update CLAUDE.md with the CMA block between markers. Returns 'created'|'updated'|'appended'."""
    block = f"{_BUNDLE_BEGIN}\n{prompt_text}\n{_BUNDLE_END}\n"
    if not target.exists():
        target.write_text(block, encoding="utf-8")
        return "created"
    existing = target.read_text(encoding="utf-8")
    if _BUNDLE_BEGIN in existing and _BUNDLE_END in existing:
        before = existing.split(_BUNDLE_BEGIN)[0]
        after = existing.split(_BUNDLE_END, 1)[1]
        target.write_text(before + block + after, encoding="utf-8")
        return "updated"
    target.write_text(existing.rstrip() + "\n\n" + block, encoding="utf-8")
    return "appended"


def _copy_agents(dest_dir: Path) -> list[str]:
    """Copy bundle/agents/*.md into dest_dir. Returns list of installed agent names."""
    import shutil

    src_dir = _bundle_root() / "agents"
    dest_dir.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for src in sorted(src_dir.glob("*.md")):
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        installed.append(src.stem)
    return installed


def _write_mcp_json(target: Path) -> str:
    """Write project-scope .mcp.json registering the cma MCP server. Returns 'created'|'merged'."""
    server_entry = {
        "command": "cma",
        "args": ["mcp", "serve", "--project", "."],
    }
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        servers = existing.get("mcpServers", {})
        servers["cma"] = server_entry
        existing["mcpServers"] = servers
        target.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        return "merged"
    payload = {"mcpServers": {"cma": server_entry}}
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return "created"


def _write_claude_settings_hooks(target: Path) -> str:
    """Register CMA hooks in .claude/settings.json. Returns 'created'|'merged'.

    Two hooks fire automatically on every task boundary:
      - UserPromptSubmit -> `cma hook user-prompt`: capture + fast retrieve + inject Context Spec
      - Stop             -> `cma hook stop`: append session summary, log the event
    """
    cma_hooks = {
        "UserPromptSubmit": [
            {
                "matcher": "",
                "hooks": [
                    {"type": "command", "command": "cma hook user-prompt"}
                ],
            }
        ],
        "Stop": [
            {
                "matcher": "",
                "hooks": [
                    {"type": "command", "command": "cma hook stop"}
                ],
            }
        ],
    }
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    else:
        existing = {}

    existing_hooks = existing.get("hooks", {})
    # Merge: for each event, replace any existing CMA hook entry but preserve other entries.
    for event_name, our_entries in cma_hooks.items():
        slots = existing_hooks.get(event_name, [])
        # Filter out previous CMA-installed slots (identified by command starting with "cma hook ")
        slots = [
            slot for slot in slots
            if not any(
                (h.get("command", "").startswith("cma hook ")) for h in slot.get("hooks", [])
            )
        ]
        slots.extend(our_entries)
        existing_hooks[event_name] = slots
    existing["hooks"] = existing_hooks

    status = "merged" if target.exists() else "created"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return status


@app.command("add")
def add(
    project_path: Path = typer.Argument(
        Path("."),
        help="Directory to add CMA to (defaults to current directory).",
    ),
    user_scope: bool = typer.Option(
        False,
        "--user",
        help="Install at user scope (~/.claude/) so the vault is available in every Claude Code session.",
    ),
) -> None:
    """Add CMA memory to a directory. One command, no prerequisites.

    What it does in this directory:
      1. Scaffolds ./cma/ if it isn't there yet (vault, config, node folders, cache)
      2. Writes ./CLAUDE.md             - prompt block teaching the agent when/how to use CMA
      3. Writes ./.claude/agents/cma-*  - four pre-built sub-agents
      4. Writes ./.mcp.json             - registers the cma MCP server pointing at this project

    All CMA-managed files live under ./cma/ to keep the agent's project root clean.
    The three things at root (CLAUDE.md, .mcp.json, .claude/) are required by Claude Code.

    Use --user to install at user scope (~/.claude/) for one shared vault across every
    Claude Code session, instead of per-project. Idempotent; re-run to update.
    """
    import subprocess

    project_path = Path(project_path).resolve()

    # Auto-scaffold the project if it doesn't exist yet.
    if not (project_path / "cma" / "config.yaml").exists():
        console.print(f"[dim]No CMA project here. Scaffolding ./cma/ at {project_path}...[/dim]")
        _scaffold_project(project_path)
        console.print(f"[green]Scaffolded[/green] ./cma/ (vault, config, node folders, cache)")

    prompt_text = _render_prompt(project_path)

    if user_scope:
        claude_dir = Path.home() / ".claude"
        claude_dir.mkdir(exist_ok=True)
        claude_md = claude_dir / "CLAUDE.md"
        agents_dir = claude_dir / "agents"
        md_status = _write_claude_md(claude_md, prompt_text)
        installed = _copy_agents(agents_dir)

        console.print(f"[green]CMA added at user scope[/green] ({md_status} CLAUDE.md)")
        console.print(f"  agents: {', '.join(installed)} -> {agents_dir}")

        cmd = [
            "claude", "mcp", "add", "-s", "user", "cma",
            "--", "cma", "mcp", "serve", "--project", str(project_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"[green]Registered MCP server[/green] (user scope)")
        else:
            console.print(f"[yellow]Could not auto-register MCP server.[/yellow] Run manually:")
            console.print(f"  [cyan]{' '.join(cmd)}[/cyan]")
            if result.stderr:
                console.print(f"  [dim]{result.stderr.strip()}[/dim]")
    else:
        claude_md = project_path / "CLAUDE.md"
        agents_dir = project_path / ".claude" / "agents"
        mcp_json = project_path / ".mcp.json"
        settings_json = project_path / ".claude" / "settings.json"

        md_status = _write_claude_md(claude_md, prompt_text)
        installed = _copy_agents(agents_dir)
        mcp_status = _write_mcp_json(mcp_json)
        hooks_status = _write_claude_settings_hooks(settings_json)

        console.print(f"[green]CMA added[/green] at {project_path}")
        console.print(f"  CLAUDE.md             ({md_status})")
        console.print(f"  .claude/agents/       {', '.join(installed)}")
        console.print(f"  .claude/settings.json ({hooks_status} - hooks for auto-firing)")
        console.print(f"  .mcp.json             ({mcp_status})")

        # Ingest the user's project files into the vault and build the index so
        # the Obsidian graph view shows real structure on first open. Skips the
        # cma/, .claude/, .git/, node_modules/, etc. dirs by default.
        console.print()
        console.print(f"[dim]Ingesting project files from {project_path} into the vault...[/dim]")
        ingest_result = ingest_sources(
            source_dir=project_path,
            project_path=project_path,
            exclude_globs=["CLAUDE.md", ".mcp.json"],
            project_name=project_path.name,
        )
        console.print(
            f"[green]Ingested[/green] {len(ingest_result.imported)} files "
            f"(skipped {len(ingest_result.skipped)})."
        )
        log_activity(
            project_path, "ingest",
            summary=f"{len(ingest_result.imported)} files ingested from {project_path.name}",
            details={"imported": len(ingest_result.imported), "skipped": len(ingest_result.skipped)},
        )

        console.print(f"[dim]Building index (BM25 + embeddings, ~30s on first run)...[/dim]")
        try:
            _run_index_build(project_path)
        except typer.Exit:
            console.print("[yellow]Index build skipped.[/yellow]")

        dashboard_path = project_path / "cma" / "memory_log" / "dashboard.html"
        console.print()
        console.print("[bold]Next steps[/bold]:")
        console.print("  1. [bold yellow]Restart Claude Code[/bold yellow] in this directory so the project-scope MCP server connects:")
        console.print(
            f"     [cyan]cd {project_path}[/cyan]\n"
            "     [cyan]claude[/cyan]   [dim](exit any existing session first)[/dim]"
        )
        console.print("  2. Open the live memory log dashboard in your browser:")
        console.print(
            f"     [cyan]file:///{str(dashboard_path).replace(chr(92), '/')}[/cyan]"
        )
        console.print("     Auto-refreshes every 5s; shows every search/retrieve/record with clickable artifact links.")
        console.print("  3. See the memory graph in Obsidian:")
        console.print(
            "     Open Obsidian -> [cyan]Open folder as vault[/cyan] -> "
            f"[cyan]{project_path / 'cma' / 'vault'}[/cyan]"
        )
        console.print("     Open graph view (Ctrl+G). Heatmap and context_spec colors are pre-configured.")


_CMA_HINT_BEGIN = "<!-- BEGIN CMA HINT -->"
_CMA_HINT_END = "<!-- END CMA HINT -->"

_CMA_HINT_BODY = """\
## CMA (Contextual Memory Architecture)

CMA is a local-first persistent memory layer for AI agents, installed as a \
Python package (the `cma` command is on PATH).

If the user asks to add CMA, install CMA, add persistent memory, set up \
Contextual Memory Architecture, or enable memory for an agent project, run \
`cma add` in that directory. This scaffolds a vault and wires the project to \
use the CMA MCP server. After it completes, tell the user to restart Claude \
Code so the project-scope MCP server connects.

For full documentation: run `cma --help`."""


@app.command("init-claude")
def init_claude(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite an existing CMA hint block."),
) -> None:
    """One-time: write a discoverability hint into ~/.claude/CLAUDE.md.

    After this runs, asking Claude Code to "add CMA" in any directory will
    trigger the agent to run `cma add` automatically. Idempotent.
    """
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(exist_ok=True)
    target = claude_dir / "CLAUDE.md"

    block = f"{_CMA_HINT_BEGIN}\n{_CMA_HINT_BODY}\n{_CMA_HINT_END}\n"

    if not target.exists():
        target.write_text(block, encoding="utf-8")
        console.print(f"[green]Created[/green] {target} with CMA hint.")
    else:
        existing = target.read_text(encoding="utf-8")
        if _CMA_HINT_BEGIN in existing and _CMA_HINT_END in existing:
            if not force:
                console.print(f"[yellow]CMA hint already present[/yellow] in {target}. Use --force to overwrite.")
                return
            before = existing.split(_CMA_HINT_BEGIN)[0]
            after = existing.split(_CMA_HINT_END, 1)[1]
            target.write_text(before + block + after, encoding="utf-8")
            console.print(f"[green]Updated[/green] CMA hint in {target}.")
        else:
            target.write_text(existing.rstrip() + "\n\n" + block, encoding="utf-8")
            console.print(f"[green]Appended[/green] CMA hint to {target}.")

    console.print(
        "\n[dim]Now in any directory, asking Claude Code to 'add CMA' or "
        "'add memory' will run `cma add` automatically.[/dim]"
    )


# -------- hooks --------

hook_app = typer.Typer(
    name="hook",
    help="Claude Code hook entry points (UserPromptSubmit, Stop). Called by the hook system, not directly.",
    no_args_is_help=True,
)
app.add_typer(hook_app, name="hook")


@hook_app.command("user-prompt")
def hook_user_prompt() -> None:
    """UserPromptSubmit hook: capture prompt, run fast retrieve, print Context Spec."""
    from cma.hooks import user_prompt_hook
    raise typer.Exit(code=user_prompt_hook())


@hook_app.command("stop")
def hook_stop() -> None:
    """Stop hook: append session summary, log the event."""
    from cma.hooks import stop_hook
    raise typer.Exit(code=stop_hook())


# -------- activity log --------


@app.command()
def activity(
    project_path: Path = typer.Argument(Path("."), help="Path to the CMA project."),
    refresh: bool = typer.Option(False, "--refresh", "-r", help="Regenerate dashboard.html from current activity.jsonl."),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of most-recent events to print."),
    event_type: str = typer.Option(None, "--type", "-t", help="Filter by event type (retrieve, search, record, index, ingest, bootstrap)."),
) -> None:
    """Show the memory log: what searches/retrieves/records the agent has done.

    Default behavior: print the last N events as a rich table to the terminal.
    Use --refresh to regenerate the HTML dashboard from the current activity.jsonl.

    The dashboard is at <project>/cma/memory_log/dashboard.html and auto-refreshes
    every 5 seconds in the browser; you usually don't need to run this command.
    """
    project_path = Path(project_path).resolve()
    events = read_events(project_path)
    if event_type:
        events = [e for e in events if e.get("type") == event_type]

    if refresh:
        html = render_dashboard_html(events, project_path)
        dashboard = project_path / "cma" / "memory_log" / "dashboard.html"
        dashboard.parent.mkdir(parents=True, exist_ok=True)
        dashboard.write_text(html, encoding="utf-8")
        console.print(f"[green]Refreshed[/green] {dashboard}")

    if not events:
        console.print(f"[dim]No activity yet for {project_path.name}.[/dim]")
        console.print(f"[dim]Run a search or retrieve in Claude Code, then come back.[/dim]")
        return

    table = Table(title=f"CMA activity — {project_path.name}", show_lines=False)
    table.add_column("Time", style="dim", width=20)
    table.add_column("Type", style="bold", width=10)
    table.add_column("Summary", overflow="fold")
    table.add_column("Artifacts", style="dim", overflow="fold")

    for ev in events[-limit:]:
        ts = ev.get("ts", "")[:19].replace("T", " ")
        t = ev.get("type", "")
        summary = ev.get("summary") or ev.get("query") or ev.get("task_id") or ""
        artifacts = ev.get("artifacts") or []
        artifact_str = ", ".join(a.get("title", "?") for a in artifacts[:3])
        if len(artifacts) > 3:
            artifact_str += f" +{len(artifacts) - 3} more"
        table.add_row(ts, t, summary, artifact_str)

    console.print(table)
    dashboard = project_path / "cma" / "memory_log" / "dashboard.html"
    if dashboard.exists():
        console.print(
            f"\n[dim]Live dashboard:[/dim] [cyan]file:///{str(dashboard).replace(chr(92), '/')}[/cyan]"
        )


if __name__ == "__main__":
    app()

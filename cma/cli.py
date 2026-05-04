"""Command-line interface for CMA."""

from __future__ import annotations

import json
import os
import pickle
from pathlib import Path

import numpy as np
import typer
import yaml
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from cma import __version__
from cma.config import CMAConfig
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
]

NODE_FOLDERS = {
    "reasoner": ["prompts", "policies", "task_frames", "outputs"],
    "retriever": ["indexes", "specs", "graph_reports", "retrieval_logs"],
    "recorder": ["completion_packages", "memory_write_proposals", "write_logs", "templates"],
}

DERIVED_FOLDERS = ["graph", "embeddings", "bm25", "cache", "state", "eval_runs"]

DEFAULT_CONFIG = """\
# Contextual Memory Architecture configuration
vault_path: ./vault
index_path: ./.cma

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

Drop markdown notes anywhere under the `vault/` folder and link them using
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


@app.command()
def init(
    project_path: Path = typer.Argument(..., help="Path to create the CMA project at."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite an existing config."),
) -> None:
    """Initialize a new CMA project with vault, node folders, and default config."""
    project_path = Path(project_path).resolve()
    project_path.mkdir(parents=True, exist_ok=True)

    config_file = project_path / "cma.config.yaml"
    if config_file.exists() and not force:
        console.print(
            f"[yellow]Config already exists at {config_file}. "
            "Use --force to overwrite.[/yellow]"
        )
        raise typer.Exit(code=1)

    config_file.write_text(DEFAULT_CONFIG, encoding="utf-8")

    for folder in VAULT_FOLDERS:
        (project_path / "vault" / folder).mkdir(parents=True, exist_ok=True)

    for node, subfolders in NODE_FOLDERS.items():
        for sub in subfolders:
            (project_path / node / sub).mkdir(parents=True, exist_ok=True)

    for sub in DERIVED_FOLDERS:
        (project_path / ".cma" / sub).mkdir(parents=True, exist_ok=True)

    welcome_path = project_path / "vault" / "000-inbox" / "Welcome.md"
    quickstart_path = project_path / "vault" / "000-inbox" / "Quickstart.md"
    if not welcome_path.exists():
        welcome_path.write_text(WELCOME_NOTE, encoding="utf-8")
    if not quickstart_path.exists():
        quickstart_path.write_text(QUICKSTART_NOTE, encoding="utf-8")

    console.print(
        Panel.fit(
            f"[green]Initialized CMA project at[/green] [bold]{project_path}[/bold]\n\n"
            "Next steps:\n"
            f"  [cyan]cd {project_path.name}[/cyan]\n"
            "  [cyan]cma setup[/cyan]          # configure your LLM/agent integration\n"
            "  [cyan]cma index[/cyan]          # train the memory graph\n"
            "  [cyan]cma graph health[/cyan]   # inspect graph structure\n"
            "  [cyan]cma retrieve \"<query>\"[/cyan]   # query the memory layer",
            title="CMA",
            border_style="green",
        )
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
      - .cma/graph/nodes.json      (node manifest)
      - .cma/bm25/index.pkl        (BM25 index)
      - .cma/embeddings/*.npy      (embeddings, if a provider is configured)
    """
    project_path = Path(project_path).resolve()
    config = _load_config(project_path)
    vault_path = Path(config.vault_path)

    if not vault_path.exists():
        console.print(f"[red]Vault not found at {vault_path}. Run `cma init` first.[/red]")
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
) -> None:
    """Run the Retriever and emit a Context Spec for the query."""
    project_path = Path(project_path).resolve()
    retriever = Retriever.from_project(project_path)

    spec = retriever.retrieve(
        query,
        max_depth=max_depth,
        beam_width=beam_width,
    )

    if json_output:
        out = spec.model_dump_json(indent=2)
        console.print(out)
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
    config_path = project_path / "cma.config.yaml"
    if not config_path.exists():
        console.print(
            f"[red]No cma.config.yaml at {project_path}. Run `cma init {project_path}` first.[/red]"
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


# -------- placeholder for Phase 6 --------


@app.command(hidden=True)
def mcp(
    action: str = typer.Argument("serve"),
    project_path: Path = typer.Option(Path("."), "--project", "-p"),
) -> None:
    """MCP server (Phase 6) - not yet implemented."""
    console.print(
        "[yellow]MCP server is not yet implemented (Phase 6).[/yellow]\n"
        "For now, integrate via the Python SDK or `cma retrieve`."
    )
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()

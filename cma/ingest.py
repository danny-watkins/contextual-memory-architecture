"""Ingest external project files into a CMA vault.

Walks a source directory, detects each file's role (documentation, code,
config, decision, pattern, ...), normalizes it into a CMA-compatible
markdown note, and writes it under `vault/020-sources/<project>/`. Also
emits one project note per top-level subdirectory under
`vault/001-projects/`.

Design notes:
- Markdown sources are inlined as native markdown (not fenced) so wikilinks
  resolve and headings render in Obsidian.
- Code/config sources are wrapped in a fenced code block.
- Filenames and titles use the file's relative path inside its project, so
  the title is human-readable and stable across re-ingests.
- Empty / trivial files are skipped via `min_chars`.
- Type is detected from filename + path conventions (README -> documentation,
  *.py -> code, decisions/* -> decision, etc.) and recorded in frontmatter.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path

import frontmatter

from cma.config import CMAConfig
from cma.recorder.writers import sanitize_filename
from cma.schemas.memory_record import MEMORY_TYPES


def _filename_for_relpath(rel_within_project: str) -> str:
    """Build a vault filename from a relpath without doubling extensions.

    Strips the source extension before sanitizing, then re-adds `.md`. If the
    sanitized stem hits the 100-char filename limit, append a short hash of
    the full relpath so collisions stay disambiguated.
    """
    p = Path(rel_within_project)
    stem = (p.parent / p.stem).as_posix() if str(p.parent) != "." else p.stem
    sanitized = sanitize_filename(stem)
    if len(sanitized) >= 100:
        digest = sha1(rel_within_project.encode("utf-8")).hexdigest()[:8]
        sanitized = f"{sanitized[:90]}-{digest}"
    return f"{sanitized}.md"


@dataclass
class IngestResult:
    """Tally of an ingest operation."""

    imported: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)
    dry_run: bool = False

    def summary(self) -> str:
        verb = "would import" if self.dry_run else "imported"
        return (
            f"{verb}={len(self.imported)} "
            f"skipped={len(self.skipped)} "
            f"errors={len(self.errors)}"
        )


DEFAULT_SOURCE_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".sql",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cma",       # legacy derived state location
    ".claude",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "example_vault",
    "cma",        # CMA's own folder under the new layout (vault, cache, node dirs)
}

CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".scss", ".sql"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
DATA_EXTENSIONS = {".txt"}

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".txt": "text",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _frontmatter(fm: dict) -> str:
    rendered = frontmatter.dumps(frontmatter.Post("", **fm))
    return "---\n" + rendered.split("---", 2)[1].strip() + "\n---"


def _read_text(path: Path, max_bytes: int) -> tuple[str | None, str | None]:
    if path.stat().st_size > max_bytes:
        return None, f"larger than max_bytes ({max_bytes})"
    try:
        raw = path.read_bytes()
    except OSError as e:
        return None, str(e)
    if b"\x00" in raw:
        return None, "binary file"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        try:
            return raw.decode("utf-8-sig"), None
        except UnicodeDecodeError:
            return None, "not utf-8 text"


def _project_name_for(source_dir: Path, file_path: Path) -> str:
    rel = file_path.relative_to(source_dir)
    if len(rel.parts) > 1:
        return rel.parts[0]
    return source_dir.name


def _relpath_within_project(source_dir: Path, file_path: Path, project_name: str) -> str:
    """Path of the file relative to its project subdir, as a posix string.

    For `source_dir/<project>/sub/file.py` -> `sub/file.py`.
    For root-level files (no project subdir match) -> the bare filename.
    """
    rel = file_path.relative_to(source_dir).as_posix()
    prefix = f"{project_name}/"
    if rel.startswith(prefix):
        return rel[len(prefix):]
    return Path(file_path).name


def _detect_type(file_path: Path, rel_within_project: str) -> str:
    """Detect a CMA memory type from filename and path conventions."""
    name = file_path.name.lower()
    stem = file_path.stem.lower()
    suffix = file_path.suffix.lower()
    parts_lower = {p.lower() for p in Path(rel_within_project).parts[:-1]}

    if stem.startswith("readme"):
        return "documentation"
    if stem.startswith(("changelog", "history", "release_notes", "releases")):
        return "changelog"

    if suffix in MARKDOWN_EXTENSIONS:
        if {"decisions", "decision", "adr", "adrs"} & parts_lower:
            return "decision"
        if {"patterns", "pattern"} & parts_lower:
            return "pattern"
        if {"docs", "doc", "documentation"} & parts_lower:
            return "documentation"
        return "documentation"

    if suffix in CODE_EXTENSIONS:
        return "code"
    if suffix in CONFIG_EXTENSIONS:
        return "config"
    if suffix in DATA_EXTENSIONS:
        return "data"

    return "source"


def _strip_existing_frontmatter(content: str) -> tuple[dict, str]:
    """If content begins with YAML frontmatter, peel it off and return (meta, body)."""
    try:
        post = frontmatter.loads(content)
        return dict(post.metadata), post.content
    except Exception:
        return {}, content


def _readme_summary(source_dir: Path, project_name: str, max_chars: int = 600) -> str | None:
    """Return the first paragraph of the project's README, if present."""
    project_root = source_dir / project_name
    candidates = ["README.md", "Readme.md", "readme.md", "README.markdown", "README.txt", "README"]
    for name in candidates:
        candidate = project_root / name
        if not candidate.is_file():
            continue
        try:
            raw = candidate.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        _meta, body = _strip_existing_frontmatter(raw)
        for paragraph in body.split("\n\n"):
            text = paragraph.strip()
            if not text:
                continue
            if text.startswith("#"):
                continue
            return text[:max_chars].rstrip()
    return None


def _render_project_note(
    *,
    project_name: str,
    sources_by_type: dict[str, list[str]],
    summary: str | None,
) -> str:
    fm = {
        "type": "project",
        "title": project_name,
        "status": "active",
        "created": _now_iso(),
        "tags": ["project", "ingested"],
        "human_verified": False,
    }
    lines = [
        _frontmatter(fm),
        "",
        f"# {project_name}",
        "",
        "## Summary",
        summary or "Project-level memory generated from imported source files.",
        "",
        "## Sources",
    ]
    type_order = ["documentation", "decision", "pattern", "code", "config", "data", "changelog", "source"]
    for type_name in type_order:
        titles = sources_by_type.get(type_name)
        if not titles:
            continue
        heading = type_name.title() if type_name != "code" else "Code"
        lines.append(f"### {heading}")
        for title in sorted(set(titles)):
            lines.append(f"- [[{title}]]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_source_note(
    *,
    title: str,
    project_name: str,
    rel_within_project: str,
    source_path: Path,
    content: str,
    max_chars: int,
    default_status: str,
    detected_type: str,
) -> str:
    suffix = source_path.suffix.lower()
    is_markdown = suffix in MARKDOWN_EXTENSIONS
    excerpt = content.strip()
    truncated = len(excerpt) > max_chars
    if truncated:
        excerpt = excerpt[:max_chars].rstrip()

    tags = [detected_type, suffix.lstrip(".") or "text"]
    if detected_type != "source":
        tags.append("source")

    fm = {
        "type": detected_type,
        "title": title,
        "status": default_status,
        "created": _now_iso(),
        "tags": tags,
        "source_project": project_name,
        "source_path": str(source_path),
        "imported_from": rel_within_project,
        "human_verified": False,
    }

    if is_markdown:
        meta, body = _strip_existing_frontmatter(excerpt)
        for key in ("type", "title", "status", "tags"):
            meta.pop(key, None)
        for key, value in meta.items():
            if key not in fm:
                fm[key] = value
        body_text = body.strip() or "_(empty markdown source)_"
    else:
        body_text = None

    lines = [
        _frontmatter(fm),
        "",
        f"# {title}",
        "",
        f"From [[{project_name}]] / `{rel_within_project}`.",
        "",
    ]

    if is_markdown:
        lines += [body_text, ""]
    else:
        language = LANGUAGE_BY_EXTENSION.get(suffix, suffix.lstrip(".") or "text")
        lines += [
            "```" + language,
            excerpt,
            "```",
            "",
        ]

    if truncated:
        lines += [
            "_Truncated to {} characters during ingestion._".format(max_chars),
            "",
        ]

    return "\n".join(lines).rstrip() + "\n"


def _path_excluded(rel_path: str, exclude_globs: list[str]) -> bool:
    for pattern in exclude_globs:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


def ingest_sources(
    source_dir: Path,
    project_path: Path,
    *,
    extensions: set[str] | None = None,
    exclude_dirs: set[str] | None = None,
    exclude_globs: list[str] | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
    max_bytes: int = 200_000,
    max_chars: int = 20_000,
    min_chars: int = 20,
    default_status: str = "proposed",
    project_name: str | None = None,
) -> IngestResult:
    """Normalize source files into Obsidian-compatible CMA notes.

    Each text file becomes one source note under
    `vault/020-sources/<project_name>/<sanitized_relpath>.md`. Each top-level
    project gets one project note under `vault/001-projects/<project>.md`.
    Markdown sources are inlined as native markdown; other files are wrapped
    in a fenced code block. Type is detected from the filename and path.
    """
    project_path = Path(project_path).resolve()
    config = CMAConfig.from_project(project_path).resolve_paths(project_path)
    vault_path = Path(config.vault_path)
    source_dir = Path(source_dir).resolve()
    extensions = {
        e.lower() if e.startswith(".") else f".{e.lower()}"
        for e in (extensions or DEFAULT_SOURCE_EXTENSIONS)
    }
    exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
    exclude_globs = list(exclude_globs or [])

    result = IngestResult(dry_run=dry_run)
    if not source_dir.exists():
        result.errors.append((source_dir, "source directory does not exist"))
        return result
    if not source_dir.is_dir():
        result.errors.append((source_dir, "source is not a directory"))
        return result
    if not vault_path.exists():
        result.errors.append((vault_path, "vault directory does not exist"))
        return result

    project_sources: dict[str, dict[str, list[str]]] = {}
    for file_path in sorted(source_dir.rglob("*")):
        if not file_path.is_file():
            continue
        # Skip the project's own vault to prevent self-ingestion when source overlaps
        # with project. The broader "cma" dir-name exclusion in DEFAULT_EXCLUDE_DIRS
        # also catches this for the standard layout, but we keep the explicit guard
        # in case someone configured a non-standard vault_path.
        if file_path.is_relative_to(vault_path):
            continue
        rel_parts = file_path.relative_to(source_dir).parts
        if any(part in exclude_dirs for part in rel_parts[:-1]):
            continue
        rel_posix = file_path.relative_to(source_dir).as_posix()
        if _path_excluded(rel_posix, exclude_globs):
            continue
        if file_path.suffix.lower() not in extensions:
            continue

        content, error = _read_text(file_path, max_bytes=max_bytes)
        if error:
            result.skipped.append((file_path, error))
            continue
        assert content is not None
        if len(content.strip()) < min_chars:
            result.skipped.append((file_path, f"content under min_chars ({min_chars})"))
            continue

        if project_name is not None:
            # Caller has fixed the project name (e.g., `cma add` ingesting the
            # project's own files into a single project bucket). Use the file's
            # full relative path under the source as its rel_within_project.
            file_project = project_name
            rel_within_project = file_path.relative_to(source_dir).as_posix()
        else:
            file_project = _project_name_for(source_dir, file_path)
            rel_within_project = _relpath_within_project(source_dir, file_path, file_project)
        title = file_path.stem
        detected_type = _detect_type(file_path, rel_within_project)

        target_dir = vault_path / "020-sources" / sanitize_filename(file_project)
        target_path = target_dir / _filename_for_relpath(rel_within_project)
        if target_path.exists() and not overwrite:
            result.skipped.append((file_path, "already exists in vault"))
            continue

        rendered = _render_source_note(
            title=title,
            project_name=file_project,
            rel_within_project=rel_within_project,
            source_path=file_path,
            content=content,
            max_chars=max_chars,
            default_status=default_status,
            detected_type=detected_type,
        )
        if dry_run:
            result.imported.append(target_path)
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path.write_text(rendered, encoding="utf-8")
            result.imported.append(target_path)

        project_sources.setdefault(file_project, {}).setdefault(detected_type, []).append(title)

    for project_name, sources_by_type in sorted(project_sources.items()):
        project_dir = vault_path / "001-projects"
        project_path_out = project_dir / f"{sanitize_filename(project_name)}.md"
        if project_path_out.exists() and not overwrite:
            continue
        summary = _readme_summary(source_dir, project_name)
        rendered = _render_project_note(
            project_name=project_name,
            sources_by_type=sources_by_type,
            summary=summary,
        )
        if dry_run:
            result.imported.append(project_path_out)
        else:
            project_dir.mkdir(parents=True, exist_ok=True)
            project_path_out.write_text(rendered, encoding="utf-8")
            result.imported.append(project_path_out)

    return result


def ingest_markdown(
    source_dir: Path,
    project_path: Path,
    *,
    target_folder: str = "000-inbox",
    default_type: str = "note",
    overwrite: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    """Walk source_dir for .md files and import each into vault/<target_folder>/.

    Args:
        source_dir: directory containing markdown files (walked recursively).
        project_path: the CMA project to import into.
        target_folder: vault subfolder for imports. Defaults to 000-inbox.
            Common alternatives: 003-decisions, 004-patterns, 007-codebase.
        default_type: frontmatter `type` value when the source has none.
        overwrite: replace existing vault notes with the same filename. Default
            False (collisions skip with reason "already exists in vault").
        dry_run: report what would happen without writing.

    Returns:
        IngestResult with imported/skipped/errors lists.

    Notes:
        - Filenames are flattened (subdirectory structure is not preserved).
          Collisions are detected by sanitized filename.
        - Each imported note gets `imported_from` and `imported_at` frontmatter.
        - If the source has no `type`, `title`, or `status` frontmatter, the
          ingester fills in defaults so the parser handles it cleanly.
    """
    project_path = Path(project_path).resolve()
    config = CMAConfig.from_project(project_path).resolve_paths(project_path)
    vault_path = Path(config.vault_path)
    target_dir = vault_path / target_folder
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    if default_type not in MEMORY_TYPES:
        default_type = "note"

    result = IngestResult(dry_run=dry_run)
    source_dir = Path(source_dir).resolve()

    if not source_dir.exists():
        result.errors.append((source_dir, "source directory does not exist"))
        return result
    if not source_dir.is_dir():
        result.errors.append((source_dir, "source is not a directory"))
        return result

    for md_file in sorted(source_dir.rglob("*.md")):
        try:
            stem = sanitize_filename(md_file.stem)
            target_path = target_dir / f"{stem}.md"

            if target_path.exists() and not overwrite:
                result.skipped.append((md_file, "already exists in vault"))
                continue

            with open(md_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            fm = dict(post.metadata)
            if "type" not in fm:
                fm["type"] = default_type
            if "title" not in fm:
                fm["title"] = md_file.stem
            if "status" not in fm:
                fm["status"] = "active"

            try:
                rel = md_file.relative_to(source_dir).as_posix()
            except ValueError:
                rel = md_file.name
            fm["imported_from"] = rel
            fm["imported_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

            new_post = frontmatter.Post(post.content, **fm)
            rendered = frontmatter.dumps(new_post)

            if dry_run:
                result.imported.append(target_path)
                continue

            target_path.write_text(rendered, encoding="utf-8")
            result.imported.append(target_path)
        except Exception as e:
            result.errors.append((md_file, str(e)))

    return result

# Documentation

- **[CMA_Whitepaper_v0.5.pdf](CMA_Whitepaper_v0.5.pdf)** — full technical reference. Architecture, every phase, every CLI command, every schema, configuration reference, ADRs, scaling tables, glossary. Read this if you're implementing or extending CMA.

A slideshow PDF is in progress and will land in a future commit.

## Regenerating the whitepaper

The whitepaper PDF is programmatically generated from `build_whitepaper.py`. Regenerated on each release so it stays in sync with the code.

```bash
pip install reportlab>=4
python docs/build_whitepaper.py    # → docs/CMA_Whitepaper_v0.5.pdf
```

The version number in the filename and document body is sourced from the `VERSION` constant at the top of the script. Bump it when you cut a new release.

## Why ReportLab and not Markdown → Pandoc

ReportLab is pure Python, no external binaries, works on every platform without a LaTeX install. The cost is that the document is described in code rather than markdown — which is actually a feature here, because it forces every release to commit the *exact* source that produced the PDF.

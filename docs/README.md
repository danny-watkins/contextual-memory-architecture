# Documentation

Two PDFs ship with each release:

- **[CMA_Whitepaper_v0.4.pdf](CMA_Whitepaper_v0.4.pdf)** — full technical reference. Architecture, every phase, every CLI command, every schema, configuration reference, ADRs, scaling tables, glossary. Read this if you're implementing or extending CMA.
- **[CMA_Slideshow_v0.4.pdf](CMA_Slideshow_v0.4.pdf)** — 12-slide intro for Claude Code users. Lighter, more visual. Read this first if you just want to know what CMA is and how to drop it into your project.

## Regenerating

Both PDFs are programmatically generated from the scripts in this directory. They're regenerated on every release so they stay in sync with the code.

```bash
pip install reportlab>=4
python docs/build_whitepaper.py    # → docs/CMA_Whitepaper_v0.4.pdf
python docs/build_slideshow.py     # → docs/CMA_Slideshow_v0.4.pdf
```

The version number in the filename and document body is sourced from the `VERSION` constant at the top of each script. Bump it when you cut a new release.

## Why ReportLab and not Markdown → Pandoc

ReportLab is pure Python, no external binaries, works on every platform without a LaTeX install. The cost is that the document is described in code rather than markdown — which is actually a feature here, because it forces every release to commit the *exact* source that produced the PDF.

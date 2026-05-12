# Documentation

- **[CMA_Whitepaper_v0.5.pdf](CMA_Whitepaper_v0.5.pdf)** — full technical reference. Architecture, every phase, every CLI command, every schema, configuration reference, ADRs, scaling tables, glossary. Read this if you're implementing or extending CMA.
- **[CMA_Slideshow_v0.5.pdf](CMA_Slideshow_v0.5.pdf)** — 17-slide intro deck. Lighter, more visual. Read this first if you just want to know what CMA is and how to drop it into your project.

## Regenerating the PDFs

Both PDFs are programmatically generated from the scripts in this directory. Regenerated on each release so they stay in sync with the code.

```bash
pip install reportlab>=4
python docs/build_whitepaper.py    # → docs/CMA_Whitepaper_v0.5.pdf
python docs/build_slideshow.py     # → docs/CMA_Slideshow_v0.5.pdf
```

Version numbers in filenames and document bodies are sourced from the `VERSION` / `OUT` constants at the top of each script. Bump them when you cut a new release.

## Why ReportLab and not Markdown → Pandoc

ReportLab is pure Python, no external binaries, works on every platform without a LaTeX install. The cost is that the document is described in code rather than markdown — which is actually a feature here, because it forces every release to commit the *exact* source that produced the PDF.

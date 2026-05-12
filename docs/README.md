# Documentation

- **[CMA_Whitepaper_v0.5.pdf](CMA_Whitepaper_v0.5.pdf)** — full technical reference. Architecture, every phase, every CLI command, every schema, configuration reference, ADRs, scaling tables, glossary. Read this if you're implementing or extending CMA.
- **[CMA_Slideshow_v0.5.pdf](CMA_Slideshow_v0.5.pdf)** — intro deck. Lighter, more visual. Read this first if you just want to know what CMA is and how to drop it into your project.

## Regenerating

The **whitepaper** is programmatically generated from `build_whitepaper.py`:

```bash
pip install reportlab>=4
python docs/build_whitepaper.py    # → docs/CMA_Whitepaper_v0.5.pdf
```

Version number is sourced from the `VERSION` constant at the top of the script. Bump it when you cut a new release.

The **slideshow** is hand-designed in a slide editor (the PowerPoint/Keynote source lives outside the repo); the PDF in this directory is the export. A minimal fallback auto-builder lives in `build_slideshow.py` for reference — it produces a different visual style and is not the canonical artifact.

## Why ReportLab and not Markdown → Pandoc

ReportLab is pure Python, no external binaries, works on every platform without a LaTeX install. The cost is that the document is described in code rather than markdown — which is actually a feature here, because it forces every release to commit the *exact* source that produced the PDF.

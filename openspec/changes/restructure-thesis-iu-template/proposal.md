## Why

The `Report_thesis/main.tex` uses a custom chapter structure that diverges from the official International University (HCMIU–VNU) thesis template, causing the exported PDF's Table of Contents and overall layout to differ from the required format. The submission must follow the IU template exactly — 8 mandatory chapters (INTRODUCTION → RELATED WORK → METHODOLOGY → PROTOTYPING → IMPLEMENTATION → RESULT → DISCUSSION → CONCLUSION), a `.bib`-based bibliography, and a single LISTINGS appendix.

## What Changes

- **Replace** the chapter block in `Report_thesis/main.tex` with the IU-required 8-chapter sequence, preserving `\pagenumbering{arabic}` and `\setcounter{page}{1}` after the first chapter
- **Rename / consolidate** the 11 existing chapter files into 8 IU-standard files: `introduction.tex`, `work.tex`, `methodology.tex`, `prototyping.tex`, `implementation.tex`, `result.tex`, `discussion.tex`, `conclusion.tex`
- **Map** existing content to correct chapters (System Overview + Data Pre-processing → Introduction; RAG v1.0 → Related Work; Agent v2.0 PATH 1 → Methodology; Agent v2.0 PATH 2 + Interface → Prototyping; PostgreSQL + End-to-End → Implementation; Evaluation conclusion → Result + Discussion + Conclusion)
- **Replace** the inline `\begin{thebibliography}{99}` block with `\bibliographystyle{ieeetr}` + `\bibliography{bibliography.bib}` and create `bibliography.bib` with all current references
- **Consolidate** the two custom appendix chapters into a single `\chapter{LISTINGS}` → `\input{chapters/appendix}` and create `chapters/appendix.tex`
- **Preserve** all preamble packages, page styles, and front-matter (title page, approval letter, acknowledgements, abstract, list of tables/figures/algorithms/listings)

## Capabilities

### New Capabilities

- `thesis-chapter-mapping`: Mapping of existing 11 content files into the 8 IU-standard chapter files
- `bibliography-bib-file`: Extraction of inline bibliography entries into a standalone `bibliography.bib` file
- `appendix-consolidation`: Merging of two appendix chapters into a single IU-compliant LISTINGS appendix

### Modified Capabilities

- (none — this is a document structure change only, not a software capability change)

## Impact

- **Files modified**: `Report_thesis/main.tex` (chapter block + bibliography section + appendix section)
- **Files created**: `Report_thesis/bibliography.bib`, `Report_thesis/chapters/introduction.tex`, `chapters/work.tex`, `chapters/methodology.tex`, `chapters/prototyping.tex`, `chapters/implementation.tex`, `chapters/result.tex`, `chapters/discussion.tex`, `chapters/conclusion.tex`, `chapters/appendix.tex`
- **Files removed/retired**: The 11 original chapter files (content moved, originals can be deleted or kept for reference)
- **No code changes** — purely LaTeX document structure

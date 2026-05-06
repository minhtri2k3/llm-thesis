## Context

The `Report_thesis/main.tex` was authored with domain-specific chapter names (System Overview, Data Pre-processing, RAG v1.0, etc.) that are meaningful for the content but do not comply with the IU thesis template structure. The IU template mandates exactly 8 chapters with fixed names and a specific front-matter/back-matter ordering. The submission PDF must produce a Table of Contents that is visually and structurally identical to the template's TOC (image 1): chapter names in uppercase bold, numbered 1–8, with the bibliography using `ieeetr` style and a single LISTINGS appendix.

## Goals / Non-Goals

**Goals:**
- `Report_thesis/main.tex` produces a PDF with a TOC identical in structure to the IU template
- Chapter names exactly match: INTRODUCTION, RELATED WORK, METHODOLOGY, PROTOTYPING, IMPLEMENTATION, RESULT, DISCUSSION, CONCLUSION
- Bibliography uses `\bibliographystyle{ieeetr}` + `\bibliography{bibliography.bib}` (external `.bib` file)
- Single appendix: `\chapter{LISTINGS}` → `\input{chapters/appendix}`
- All existing content is preserved and redistributed into the new chapter files
- The preamble (packages, page styles, front-matter) remains unchanged

**Non-Goals:**
- Changing any content/text within the chapters
- Modifying the IU template files (read-only reference)
- Changing the Docker, API, or any non-LaTeX code

## Decisions

### D1 — Content mapping strategy
**Decision**: Map the 11 existing chapter files into 8 new IU-standard files by logical grouping, using `\input{}` chains inside each new file where content spans multiple originals.

| New IU file | Content sources |
|---|---|
| `chapters/introduction.tex` | `system_overview.tex` + `data_preprocessing.tex` |
| `chapters/work.tex` | `rag_v1_architecture.tex` |
| `chapters/methodology.tex` | `agent_v2_path1.tex` (core methodology) |
| `chapters/prototyping.tex` | `agent_v2_path2.tex` + `end_to_end_example.tex` |
| `chapters/implementation.tex` | `postgresql_integration.tex` + `interface_deployment.tex` |
| `chapters/result.tex` | first half of `evaluation_conclusion.tex` (evaluation metrics section) |
| `chapters/discussion.tex` | middle of `evaluation_conclusion.tex` (analysis/limitations section) |
| `chapters/conclusion.tex` | final section of `evaluation_conclusion.tex` (conclusion/future work) |
| `chapters/appendix.tex` | merged from `appendix_equations.tex` + `appendix_configs.tex` |

**Rationale**: Using `\input{}` inside new chapter files means we don't have to duplicate or delete the original files — they become sub-inputs, preserving a clean content audit trail.

### D2 — Bibliography approach
**Decision**: Extract all 14 `\bibitem` entries from the inline `thebibliography` environment into a proper `bibliography.bib` file with BibTeX format, and replace the block with `\bibliographystyle{ieeetr}` + `\bibliography{bibliography.bib}`.

**Rationale**: The IU template uses an external `.bib` file. The `ieeetr` style produces numbered `[1]` citations matching the required format. This also makes the bibliography maintainable.

### D3 — Appendix structure
**Decision**: Replace the two custom appendix chapters (`Supplementary Equations` and `Sample Configuration Files`) with a single `\chapter{LISTINGS}` that `\input{chapters/appendix}`, where `appendix.tex` contains both former appendix files via `\input`.

**Rationale**: The IU template has exactly one appendix chapter named LISTINGS. Merging both into one chapter via sub-inputs keeps all content while matching the required structure.

### D4 — Original files
**Decision**: Keep the original 11 chapter files intact (do not delete). The new IU-standard files will `\input` them.

**Rationale**: Safer approach — no content is lost. The originals serve as verified content that is simply re-routed through new chapter wrappers.

## Risks / Trade-offs

- **Content split risk**: `evaluation_conclusion.tex` spans result + discussion + conclusion — splitting into 3 logical sections requires reading the file and inserting section breaks. The split must be at natural section boundaries.  
  → **Mitigation**: Read `evaluation_conclusion.tex` before splitting; preserve all `\section{}` headings intact.

- **`\pagenumbering{arabic}` placement**: Must remain immediately after `\chapter{INTRODUCTION}` — not move to any other chapter.  
  → **Mitigation**: Strictly follow the IU template's line sequence.

- **Bibliography `.bib` key consistency**: Citation keys in `\cite{}` calls throughout chapter files must match the new BibTeX keys in `bibliography.bib`.  
  → **Mitigation**: Preserve existing `\bibitem` keys as BibTeX entry IDs (e.g., `lewis2020rag` stays `lewis2020rag`).

- **Compile warnings**: Moving from `thebibliography` to BibTeX requires running `pdflatex → bibtex → pdflatex → pdflatex`. The PDF viewer must be refreshed.  
  → **Mitigation**: Document the 4-pass compile sequence in a comment in `main.tex`.

## Migration Plan

1. Read `evaluation_conclusion.tex` to identify the natural result/discussion/conclusion split points
2. Create `bibliography.bib` with all 14 entries in BibTeX format
3. Create 9 new chapter files (`introduction.tex`, `work.tex`, `methodology.tex`, `prototyping.tex`, `implementation.tex`, `result.tex`, `discussion.tex`, `conclusion.tex`, `appendix.tex`) each using `\input{}` to pull in originals
4. Rewrite the chapter block and bibliography/appendix sections of `main.tex`
5. Verify compile: `pdflatex main` → `bibtex main` → `pdflatex main` → `pdflatex main`
6. Confirm TOC matches image (1)

## Open Questions

- Does `evaluation_conclusion.tex` have clear `\section` markers that align with Result / Discussion / Conclusion boundaries? (Check before splitting.)
- Should the PATH 2 content (`agent_v2_path2.tex`) stay in Prototyping, or should it move to Implementation? (Prototyping is recommended since PATH 2 is not yet fully implemented.)

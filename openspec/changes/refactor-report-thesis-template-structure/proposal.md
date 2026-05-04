## Why

The current thesis source in `fashion_agent/documents/Report_thesis/thesis_report.tex` is maintained as a single large file, which makes IU template alignment difficult to verify and update. The report also needs front-matter and table-of-contents behavior to follow the IU LaTeX template consistently.

## What Changes

- Refactor `Report_thesis` from a monolithic `thesis_report.tex` into a template-style orchestrator layout with `main.tex` and chapter-level `\input{chapters/...}` files.
- Align front-matter sequencing and TOC-related pages with the IU template pattern:
  - Table of Contents
  - List of Tables
  - List of Figures
  - List of Algorithms
  - List of Listings
  - Abstract
- Keep Approval Letter and Acknowledgements as front matter but remove them from TOC.
- Remove `List of Abbreviations` and `List of Symbols` sections from the thesis document structure.
- Preserve existing technical chapter content while relocating it to separated chapter files.

## Capabilities

### New Capabilities
- `thesis-latex-template-conformance`: Define template-conformant thesis document structure, front-matter ordering, TOC/list behavior, and modular chapter composition for `Report_thesis`.

### Modified Capabilities
- None.

## Impact

- Affected source: `fashion_agent/documents/Report_thesis/thesis_report.tex`, `fashion_agent/documents/Report_thesis/main.tex`, and `fashion_agent/documents/Report_thesis/chapters/*.tex`.
- Affected behavior: LaTeX document assembly order, front-matter navigation entries, and maintainability of thesis sources.
- No runtime API or application-service impact; scope is documentation/build artifact generation for thesis LaTeX sources.

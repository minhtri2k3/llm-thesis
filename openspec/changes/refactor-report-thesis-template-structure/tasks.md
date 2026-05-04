## 1. Prepare controller structure

- [x] 1.1 Promote `fashion_agent/documents/Report_thesis/main.tex` to the canonical controller file for thesis assembly.
- [x] 1.2 Move preamble and shared document-level configuration from `thesis_report.tex` into `main.tex`.
- [x] 1.3 Define chapter include mapping for all existing chapter boundaries in the monolithic source.

## 2. Split monolithic content into chapter files

- [x] 2.1 Extract each main chapter body into `chapters/*.tex` files (`system_overview`, `data_preprocessing`, `rag_v1_architecture`, `postgresql_integration`, `agent_v2_path1`, `agent_v2_path2`, `end_to_end_example`, `interface_deployment`, `evaluation_conclusion`).
- [x] 2.2 Extract appendix chapter bodies into separate files (`appendix_equations`, `appendix_configs`) and wire them through `\appendix` in `main.tex`.
- [x] 2.3 Rebuild chapter order in `main.tex` using `\chapter{...}` + `\input{chapters/...}` while preserving labels and citations.

## 3. Align front matter and TOC behavior

- [x] 3.1 Keep Approval Letter and Acknowledgements pages in front matter but remove their TOC insertions.
- [x] 3.2 Enforce list ordering in `main.tex`: TOC → List of Tables → List of Figures → List of Algorithms → List of Listings → Abstract.
- [x] 3.3 Keep Abstract as a TOC entry and remove `List of Abbreviations` and `List of Symbols` sections from the assembly flow.
- [x] 3.4 Preserve roman-to-arabic page-numbering transition points before Chapter 1.

## 4. Finalize and verify thesis assembly

- [x] 4.1 Ensure bibliography and appendix assembly remain intact after modularization.
- [x] 4.2 Build the thesis document and fix any compile/reference issues introduced by the split.
- [x] 4.3 Confirm chapter content is fully preserved (no missing or duplicated chapter blocks) and TOC/list pages match the approved structure.

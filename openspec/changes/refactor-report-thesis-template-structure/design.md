## Context

`fashion_agent/documents/Report_thesis/thesis_report.tex` currently contains preamble, front matter, all chapters, references, and appendices in one file. This structure makes template-conformance updates risky because TOC/list ordering, front-matter inclusion, and chapter boundaries are tightly coupled in a single document.

The IU template pattern organizes the thesis as a controller document that declares global formatting and chapter sequence, while chapter bodies are separated into `chapters/*.tex` and included with `\input{...}`. The requested change also includes specific front-matter behavior decisions:

- Keep Approval Letter and Acknowledgements, but do not include them in TOC.
- Use the list sequence: TOC, List of Tables, List of Figures, List of Algorithms, List of Listings, then Abstract.
- Remove List of Abbreviations and List of Symbols sections.

## Goals / Non-Goals

**Goals:**
- Convert `Report_thesis` into a modular IU-template-style structure with a controller `main.tex`.
- Preserve existing thesis technical content while relocating it into chapter-specific files.
- Make TOC/list behavior explicit, deterministic, and aligned with selected template ordering.
- Keep LaTeX build compatibility for current thesis compilation workflow.

**Non-Goals:**
- Rewriting chapter technical content or changing scientific claims.
- Redesigning visual style beyond what is required for template-conformant structure and navigation.
- Changing bibliography entries/citations content.

## Decisions

### 1. Use `main.tex` as the orchestration entry point
**Decision:** Move document assembly responsibilities to `main.tex` (preamble + front matter + chapter ordering + references + appendices) and keep chapter content in `chapters/*.tex`.

**Rationale:** This mirrors the IU template structure and localizes sequencing concerns to one file.

**Alternatives considered:**
- Keep monolithic `thesis_report.tex` and only patch TOC commands.  
  Rejected because it keeps long-term maintenance complexity and weak separation.
- Split by section rather than by chapter.  
  Rejected because chapter-level splits are clearer and match template idioms.

### 2. Preserve chapter boundaries based on existing `\chapter{...}` markers
**Decision:** Use current chapter boundaries in `thesis_report.tex` as the migration partition map.

**Rationale:** Existing boundaries are already clean and semantically meaningful, minimizing migration risk.

**Alternatives considered:**
- Reorganize chapter order during split.  
  Rejected to avoid introducing scope creep and content-review overhead.

### 3. Encode front-matter TOC behavior explicitly
**Decision:** Apply explicit TOC inclusion/exclusion rules:
- Exclude Approval Letter and Acknowledgements from TOC.
- Include Abstract in TOC.
- Include list pages in the agreed sequence.

**Rationale:** Explicit rules prevent accidental drift and ensure stable output across edits.

**Alternatives considered:**
- Rely on default LaTeX behavior for unnumbered chapters/lists.  
  Rejected because defaults are inconsistent with required output.

### 4. Remove Abbreviations/Symbols as structural sections
**Decision:** Remove List of Abbreviations and List of Symbols sections entirely from the document flow.

**Rationale:** This is explicitly requested for the strict template mode in this change.

**Alternatives considered:**
- Keep sections but hide from TOC.  
  Rejected due to explicit removal requirement.

## Risks / Trade-offs

- **[Risk] Missing or duplicate content during chapter extraction** → **Mitigation:** Use chapter-marker-driven extraction and verify one-to-one mapping between original chapters and new files.
- **[Risk] Broken cross-references after split** → **Mitigation:** Keep labels and citation keys unchanged in extracted content; avoid renaming labels during migration.
- **[Risk] TOC/list pagination differences after restructuring** → **Mitigation:** Preserve page-numbering transition points and maintain explicit front-matter order.
- **[Trade-off] More files to manage** → **Mitigation:** Gains in maintainability and template compliance outweigh minor file-management overhead.

## Migration Plan

1. Introduce `main.tex` as canonical assembly file for `Report_thesis`.
2. Extract each chapter body from monolithic file into `chapters/<chapter_name>.tex`.
3. Reconstruct chapter sequence in `main.tex` using `\chapter{...}` + `\input{chapters/...}`.
4. Apply front-matter sequence and TOC inclusion/exclusion rules from this change.
5. Remove Abbreviations and Symbols sections from the assembly flow.
6. Keep references and appendices in the controller flow with modular inputs where applicable.
7. Compile and compare generated structure to ensure no chapter content loss.

## Open Questions

- Should `thesis_report.tex` remain as a compatibility wrapper that `\input`s `main.tex`, or be fully deprecated after migration?
- Should future front-matter pages (if added later) default to TOC exclusion unless explicitly added?

## Why

The methodology chapter in `Report_thesis_2/chapters/methodology.tex` currently has only Section 3.1 written; sections 3.2 through 3.6 are empty stubs. The richer source material in `Report_thesis/chapters/` (data preprocessing, RAG v1 architecture, agent v2 path 1 and path 2, postgres integration, evaluation) was authored against an earlier chapter layout and uses `lstlisting` Python/SQL code blocks. The new thesis must (a) follow the new section structure, (b) reflect the *current* source code in `fashion_agent/`, and (c) replace every code listing with formal algorithms or schema tables — keeping the text suitable for a thesis examiner rather than an engineering handbook.

## What Changes

- Fill empty sections 3.2, 3.3, 3.4 (with 3.4.1 + 3.4.2), 3.5, 3.6 of `Report_thesis_2/chapters/methodology.tex`.
- Reuse from `Report_thesis/`: TikZ diagrams (PATH 2 image-search flow), tables (7-intent classification, slot weights, PATH 1 vs PATH 2, evaluation metrics, validity checks, claim-evidence mapping), equations (RRF, token aggregation, cart-add/will-buy/conversion rates), and existing algorithms (ClassifyIntent, MergeSessionSlots, IsQueryReady, Cross-Modal Encoding, BM25 Composition, BM25 Scoring, RRF Fusion, Cosine Similarity, EncodeQueryImage, Direct Routing).
- **BREAKING for content style**: Convert every `lstlisting` Python/SQL block into either an `algorithm` environment (pseudocode) or a LaTeX schema table. No code blocks remain in `methodology.tex`.
- Add a "Source: `path/file.py`" note under each algorithm caption for examiner traceability.
- Add newly authored algorithms that reflect the live code: `BuildMultiVectorIndex`, `HybridSearch` (7-stage), `ExpandQuery`, `BGERerankBlend` (with the 0.7/0.3 score blend), `ResolveSearchQuery`, `SynthesizeResponse`, `FilterByGender`, `ValidatePNGUpload`, `LogQueryHistory`, `AddLikedItem`, `GetPreferences`.
- Section 3.6 covers methodology-only setup (metric definitions, cohort/inclusion-exclusion rules, validity checks, experimental matrix). No empirical numbers — those belong in Results.
- Leave Section 3.1 untouched.

## Capabilities

### New Capabilities

- `thesis-methodology-v2-content`: The completed Chapter 3 of Report_thesis_2 — a methodology chapter that documents the data acquisition pipeline, agentic reasoning engine, multi-modal retrieval pipelines, deterministic execution layer, and evaluation framework, all expressed in algorithmic form aligned with the live source code under `fashion_agent/`.

### Modified Capabilities

(none — Report_thesis_2 has no prior committed methodology spec to amend.)

## Impact

- **Affected files**: `fashion_agent/documents/Report_thesis_2/chapters/methodology.tex` (the only file modified). PDF will need to be re-built by the user (`pdflatex`/`latexmk`); we do not regenerate the PDF here.
- **Source coupling**: Each algorithm cites a file path under `fashion_agent/`. If those files are renamed later, the citations become stale; this is documented as a maintenance risk.
- **No changes** to source code, datasets, infrastructure, or `Report_thesis/` (the legacy chapter layout). PostgreSQL/Qdrant/Docker setup is untouched.
- **Reader-facing**: Length of `methodology.tex` grows from ~80 lines to ~700–900 lines.

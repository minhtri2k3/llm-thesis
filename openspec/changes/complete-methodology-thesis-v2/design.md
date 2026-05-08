## Context

`Report_thesis_2/chapters/methodology.tex` has Section 3.1 written and Sections 3.2–3.6 as empty stubs. Most of the technical content already exists, in narrative form, scattered across `Report_thesis/chapters/`:

- `data_preprocessing.tex` — dataset, cleaning, caption/color enrichment
- `rag_v1_architecture.tex` — FashionSigLIP, BM25, RRF, Qdrant
- `postgresql_integration.tex` — schema, data access layer
- `agent_v2_path1.tex` — five-step agent pipeline (intent, gate, memory, route, synthesis)
- `agent_v2_path2.tex` — image-to-image search
- `evaluation_conclusion.tex` — metrics, validity, claim mapping

That source content uses `lstlisting` blocks for Python and SQL. The new chapter must use **algorithms** and **schema tables** instead, while staying faithful to the *current* code under `fashion_agent/` (not the snapshot frozen in the older chapters). The agent code has evolved (six slots, ranked-slot readiness, BGE rerank score blending, three-way RRF, query expansion gate, gender filter, PNG validation, etc.), so several algorithms must be authored fresh — they are not just copies.

**Stakeholders**: thesis examiners (need rigorous formal presentation), the author (must defend technical choices), and future maintainers (the algorithm citations let them locate the implementation).

## Goals / Non-Goals

**Goals:**
- Produce a self-contained Chapter 3 that an examiner can read without referring to the source code, but with breadcrumbs (file paths) for those who want to verify.
- Convert every Python/SQL listing into algorithmic pseudocode or schema tables — no executable code in the chapter.
- Keep the 5-step agent narrative consistent with the diagram already in 3.1.2 and with the current code in `agent/fashion_agent.py`.
- Reuse existing tables, equations, and TikZ diagrams from `Report_thesis/` verbatim where they are still accurate.
- Section 3.6 documents the *evaluation methodology* (definitions, cohorts, validity), not empirical results.

**Non-Goals:**
- Rebuilding the PDF (`thesis_report.pdf`) — that is the user's compile step.
- Rewriting Section 3.1 (already coherent and signed off).
- Modifying any source code in `fashion_agent/` — this is a documentation-only change.
- Touching `Report_thesis/` (legacy layout retained as-is).
- Producing the empirical numbers or results tables (those go in the Results chapter, out of scope here).
- Adding new capabilities to the agent or new evaluation metrics not already implemented.

## Decisions

### D1. Convert code listings to algorithms (vs. keep Python verbatim)

**Decision:** All `lstlisting` Python blocks become `algorithm` environments with `algorithmic` pseudocode. SQL `CREATE TABLE` blocks become LaTeX schema tables (column / type / description).

**Rationale:** The user explicitly required this. Pseudocode is more rigorous for a thesis (language-independent), forces clearer specification, and decouples the document from incidental Python idioms. Schema tables are friendlier than DDL for readers focused on data semantics.

**Alternatives considered:**
- *Keep Python verbatim* — rejected; user instruction.
- *Pseudocode + appendix with full Python listings* — rejected as overkill; the algorithms already cite the source path, which serves the same audit purpose without bloating the chapter.

### D2. Cite source files under each algorithm caption

**Decision:** Each algorithm gets a small `\textit{Source: \texttt{path/file.py}}` line directly after the caption.

**Rationale:** A thesis needs traceability — examiners can audit, and it answers the implicit question "is this real or aspirational?" The user confirmed this preference.

**Trade-off:** Citations rot when files are renamed. Accepted; flagged in Risks.

### D3. Reuse vs. re-author algorithms

**Decision:** Algorithms that already match current code are reused verbatim from `Report_thesis/`. Algorithms that drifted from current code are re-authored from the source files. New algorithms are added where the live code goes beyond what the older chapter described.

| Algorithm | Action | Reason |
|---|---|---|
| ClassifyIntent | Reuse + extend | Current code has 6 slots, not just intent+confidence — extend pseudocode to reflect `ExtractedSlots`. |
| MergeSessionSlots | Reuse | Matches `slot_completeness.merge_slots` and TTLCache logic. |
| IsQueryReady | Reuse | Matches the readiness check in `agent/fashion_agent.py`. |
| Cross-Modal Encoding | Reuse | Matches `indexing/build_index.py:FashionEmbedder`. |
| BM25 Composition / Scoring | Reuse | Matches `indexing/build_index.py:compose_bm25_content` and standard BM25. |
| RRF Fusion | Reuse | Matches `search/fusion.py`. |
| EncodeQueryImage | Reuse | Matches `search/image_query_engine.py`. |
| Direct Routing OrchestrateStream | Reuse | Matches `agent/fashion_agent.py:_orchestrate_stream`. |
| Data Ingestion & Noise Filtering | Reuse | Matches `pre_processing/processing_data.py`. |
| Multimodal Caption + Color Enrichment | Reuse | Matches `pre_processing/processing_data.py`. |
| BuildMultiVectorIndex | **New** | The legacy chapter never showed a single index-build algorithm; current code has named-vector init + per-batch encode + upsert + payload composition. |
| HybridSearch (7 stages) | **New** | Older `search()` had fewer stages and different weights; the live `search/search_engine.py:search()` has expansion gate + 3-way RRF + filter-aware scoring + soft filter + rerank blend + min-score threshold. |
| ExpandQuery | **New** | Short-query gate (< 6 words) + Gemini synonyms + JSON parse fallback. |
| BGERerankBlend | **New** | The 0.7×reranker + 0.3×RRF blend is in `search/reranker.py:BGEReranker.rerank` and was never formalised. |
| ResolveSearchQuery | **New** | Captures the confidence-gate / readiness-gate decision tree in `agent/fashion_agent.py:_resolve_search_query`. |
| SynthesizeResponse | **New** (replaces Python listing) | Pseudocode form of `_synthesize_response`. |
| FilterByGender | **New** | The gender-aware post-filter in `_filter_by_gender`. |
| ValidatePNGUpload | **New** (replaces Python listing) | Pseudocode form of `_validate_path2_png_upload`. |
| LogQueryHistory / AddLikedItem / GetPreferences | **New** (replaces Python listing) | Pseudocode form of the JSONB writes/reads in `agent/memory.py`. |
| BuildClarification (template) | **New** | Pseudocode form of the deterministic-template branch in `_resolve_search_query`; references `slot_completeness.build_template_question`. |

### D4. Preserve TikZ diagrams as-is

**Decision:** Reuse the PATH 2 image-search TikZ diagram from `agent_v2_path2.tex` verbatim under 3.4.2. Section 3.1.2 already has the v2.0 5-step diagram — leave it.

**Rationale:** The diagrams are technically correct and visually consistent with the rest of the thesis. Re-drawing introduces drift risk.

### D5. Six-slot extraction (vs. four-slot)

**Decision:** The slot-extraction narrative in 3.3 reflects the current six-slot model (`category`, `color`, `fabric`, `fit`, `construction`, `aesthetic`) from `agent/intent_classifier.py:ExtractedSlots`, plus `selected_numbers`. The four-slot weight table from `agent_v2_path1.tex` (category/color/style/occasion) stays for the *ranked-slot readiness scoring* — these are two different mechanisms in the live code (`slot_completeness.check_slot_completeness` is the six-slot search threshold, while ranked-slot weights drive the search-confidence gate).

**Rationale:** Both mechanisms coexist in the code. Documenting only one would misrepresent the system. The chapter explains the relationship: six-slot extraction populates the LLM-provided slots, the ranked four-slot weighting evaluates *readiness for retrieval*.

**Alternatives considered:**
- *Drop the four-slot weight table* — rejected; the readiness gate algorithm uses it explicitly.
- *Merge into one combined table* — rejected; conflates two distinct mechanisms.

### D6. Section 3.6 scope: methodology only

**Decision:** 3.6 defines metrics, cohorts, validity gates, and the experimental matrix. No empirical numbers, no comparison tables of "RAG v1.0 vs Agent v2.0".

**Rationale:** User's chosen option. Keeps Methodology and Results separated, aligned with thesis convention (methodology states the protocol; results report what came out of running it).

**Trade-off:** The reader has to flip to the Results chapter for any numbers. Acceptable — that is the standard thesis structure.

### D7. Minimum-score threshold and `min_results` floor

**Decision:** Document the `MIN_SCORE_THRESHOLD = 0.25` and the `min_results = 1` guarantee from `search_engine.py:search()` as part of the HybridSearch algorithm.

**Rationale:** This is a non-obvious behaviour — the system trades precision for "always show *something*" when no item clears the threshold. Examiners need to know this to evaluate retrieval-quality claims fairly.

## Risks / Trade-offs

- **[Source-citation rot]** → Mitigation: keep citations to module-level paths (`search/search_engine.py`) rather than line numbers; if a file is renamed, the chapter has a single grep-friendly token. A future change should regenerate citations from a script.
- **[Drift between chapter and code]** → Mitigation: each algorithm cites its source file so a future maintainer can diff. Accepted that this is a manual sync — there is no automated tie.
- **[Length explosion]** → The chapter will roughly 10× in length. Mitigation: keep prose tight, lean on tables/algorithms over paragraphs, group related algorithms under a single explanation.
- **[Six-slot vs four-slot confusion]** → Mitigation: D5 explains the two mechanisms explicitly; the chapter introduces the six-slot extraction first, then the readiness-weight table separately, with a sentence linking them.
- **[Reused TikZ diagram from old layout uses 512-d in subtitle]** → The old PATH 2 diagram says "512-dim vector" in an arrow label. Current code is 768-d. Fix in the reused TikZ before pasting into 3.4.2.
- **[`bibliography.bib` citations]** → Some sentences in `Report_thesis/` reference papers that may not be in `Report_thesis_2/bibliography.bib`. Mitigation: avoid citing new papers in 3.2–3.6 unless we verify the entry exists; prefer self-contained prose. (The existing 3.1 already takes this approach.)

## Migration Plan

1. Apply edits to `methodology.tex` only.
2. User compiles `Report_thesis_2/main.tex` with `pdflatex` / `latexmk` and reviews the rendered PDF.
3. Rollback strategy: `git checkout HEAD -- fashion_agent/documents/Report_thesis_2/chapters/methodology.tex`. The chapter is a single file, so reversion is one command.

## Open Questions

- Are there other forthcoming sections in `Report_thesis_2` (implementation, results, discussion) that will need cross-references to specific algorithm/equation labels in this methodology? → For now, every algorithm gets a stable label like `alg:hybrid_search`; cross-references can be wired up when those chapters are written.
- Should the multilingual clarification templates (English / Vietnamese / Spanish) appear in 3.3 or in an appendix? → Default: brief mention in 3.3 (one short table or paragraph), full template list deferred to appendix if the chapter would otherwise overflow.

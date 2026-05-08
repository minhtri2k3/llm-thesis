## 1. Pre-flight: Cross-check live source before drafting

- [x] 1.1 Read `fashion_agent/agent/intent_classifier.py` to confirm the six-slot `ExtractedSlots` shape and `selected_numbers` field
- [x] 1.2 Read `fashion_agent/agent/slot_completeness.py` to confirm ranked-slot weights and `check_slot_completeness` thresholds
- [x] 1.3 Read `fashion_agent/agent/fashion_agent.py` for `_orchestrate_stream`, `_resolve_search_query`, `_synthesize_response`, `_filter_by_gender`, and the TTLCache session keys
- [x] 1.4 Read `fashion_agent/search/search_engine.py:search()` and confirm 7-stage pipeline, RRF weights (BM25=2.5, img=1.0, text=1.5, k=60), `MIN_SCORE_THRESHOLD = 0.25`, and `min_results = 1` floor
- [x] 1.5 Read `fashion_agent/search/reranker.py` to confirm the `0.7 × reranker + 0.3 × RRF` blend and BGE model identifier
- [x] 1.6 Read `fashion_agent/search/query_expansion.py` for the < 6-word gate and Gemini synonym expansion
- [x] 1.7 Read `fashion_agent/search/fusion.py` for the exact RRF formula
- [x] 1.8 Read `fashion_agent/indexing/build_index.py` for named-vector init, encode-batch, payload composition, and Qdrant upsert
- [x] 1.9 Read `fashion_agent/agent/memory.py` for `LogQueryHistory`, `AddLikedItem`, `GetPreferences` JSONB writes/reads
- [x] 1.10 Read `fashion_agent/api/main.py` for `_validate_path2_png_upload` (size cap, MIME check, PIL integrity check)
- [x] 1.11 Read `fashion_agent/pre_processing/processing_data.py` to confirm ingestion + caption + color enrichment is unchanged from the legacy chapter
- [x] 1.12 Open `Report_thesis/chapters/data_preprocessing.tex`, `rag_v1_architecture.tex`, `postgresql_integration.tex`, `agent_v2_path1.tex`, `agent_v2_path2.tex`, `evaluation_conclusion.tex` to identify exact reusable blocks (tables, equations, TikZ, algorithms)
- [x] 1.13 Open `fashion_agent/documents/Report_thesis_2/chapters/methodology.tex` and verify Section 3.1 boundaries (lines for 3.1.1 + 3.1.2 closing) so no edits cross into 3.1
- [x] 1.14 Confirm `Report_thesis_2/bibliography.bib` entries exist for any `\cite{}` calls planned in 3.2–3.6; otherwise rephrase to avoid missing citations
- [x] 1.15 Confirm `Report_thesis_2/main.tex` (or preamble) loads `algorithm`, `algorithmicx` (or `algpseudocode`), `booktabs`, `tikz` — required by the new content

## 2. Section 3.2: Data Acquisition and Knowledge Base Construction

- [x] 2.1 Write subsection prose for "Dataset" and reuse the four-column dataset description table from `Report_thesis/chapters/data_preprocessing.tex` verbatim
- [x] 2.2 Reuse algorithm `DataIngestionAndNoiseFiltering` from `Report_thesis/chapters/data_preprocessing.tex`, add `\textit{Source: \texttt{pre\_processing/processing\_data.py}}` under caption
- [x] 2.3 Reuse algorithm `MultimodalCaptionAndColorEnrichment` from `data_preprocessing.tex`, add Source line
- [x] 2.4 Author "PostgreSQL Schema" subsection — convert SQL `CREATE TABLE` blocks for `fashion_items`, `sessions`, `session_messages`, `fashion_item_enrichment` into LaTeX `tabular` / `booktabs` schema tables (Column / Type / Description). Zero SQL listings allowed
- [x] 2.5 Replace the legacy "Data Access Layer" Python listings with prose describing the read/write boundaries (no Python remaining)
- [x] 2.6 Author "Vector Index Construction" subsection — describe Qdrant collection `fashion_products`, named vectors (`image_vector`, `text_vector`, both 768-d cosine), payload fields
- [x] 2.7 Author new algorithm `BuildMultiVectorIndex` (image-vector encode → text-vector encode → BM25 content composition → Qdrant upsert with named vectors and payload). Cite `indexing/build_index.py`
- [x] 2.8 Reuse algorithms `CrossModalEncoding`, `BM25Composition`, `BM25Scoring` from `rag_v1_architecture.tex`, add Source lines (point to `indexing/build_index.py` and `search/bm25_index.py`)

## 3. Section 3.3: The Agentic Reasoning Engine

- [x] 3.1 Author overview prose linking the 5-step diagram in 3.1.2 to the deeper subsections that follow
- [x] 3.2 Reuse the 7-intent classification table (text_search / outfit_request / follow_up / product_select / view_selections / out_of_scope / unclear) from `agent_v2_path1.tex`
- [x] 3.3 Reuse + extend algorithm `ClassifyIntent` to reflect six-slot `ExtractedSlots` plus `selected_numbers`. Add Source: `agent/intent_classifier.py`
- [x] 3.4 Author "Short-Term Memory (TTLCache)" subsection — describe `_session_accumulated_slots`, `_session_ranked_slots`, `_session_last_results`, `_session_pending_selection`, TTL=1800s, category-change reset
- [x] 3.5 Reuse algorithm `MergeSessionSlots` from `agent_v2_path1.tex`, add Source: `agent/slot_completeness.py`
- [x] 3.6 Reuse the slot-weight table {category=4, color=3, occasion=3, style=2} and reuse algorithm `IsQueryReady` with the 0.75 search-confidence threshold
- [x] 3.7 Add the disambiguation paragraph required by D5: six-slot extraction populates the LLM-provided slots; the four-slot ranked weighting evaluates retrieval readiness — both coexist
- [x] 3.8 Author algorithm `BuildClarification` (deterministic-template branch of `_resolve_search_query`), cite `agent/slot_completeness.py:build_template_question`
- [x] 3.9 Brief mention of multilingual templates (English / Vietnamese / Spanish) — short table or paragraph; defer the full template list to appendix if length grows
- [x] 3.10 Author "Long-Term Memory (PostgreSQL JSONB)" subsection
- [x] 3.11 Author algorithm `LogQueryHistory` (JSONB append). Cite `agent/memory.py`
- [x] 3.12 Author algorithm `AddLikedItem`. Cite `agent/memory.py`
- [x] 3.13 Author algorithm `GetPreferences`. Cite `agent/memory.py`
- [x] 3.14 Verify zero Python listings remain in 3.3

## 4. Section 3.4.1: Text-to-Image Pipeline

- [x] 4.1 Author opening prose stating the cross-modal motivation (text query → unified embedding space with images)
- [x] 4.2 Reuse algorithm `CrossModalEncoding` (FashionSigLIP, 768-d) — add Source: `indexing/build_index.py:FashionEmbedder`
- [x] 4.3 Reuse the RRF fusion equation `score(d) = sum_r w_r/(k + rank_r(d) + 1)` with stable label (e.g., `eq:rrf`) for cross-references
- [x] 4.4 Reuse algorithm `RRFFusion` and `CosineSimilarity` from `rag_v1_architecture.tex`, add Source lines
- [x] 4.5 Author new algorithm `ExpandQuery` — short-query gate (< 6 words), Gemini synonyms, JSON parse fallback. Cite `search/query_expansion.py`
- [x] 4.6 Author new algorithm `BGERerankBlend` — pairwise scoring with BAAI/bge-reranker-v2-m3, blended score `0.7 × reranker + 0.3 × RRF`. Cite `search/reranker.py`
- [x] 4.7 Author new algorithm `HybridSearch` covering all 7 stages with explicit RRF weights (BM25=2.5, img=1.0, text=1.5, k=60), the soft RapidFuzz filter, the rerank blend, the `MIN_SCORE_THRESHOLD = 0.25` and `min_results = 1` floor. Cite `search/search_engine.py`
- [x] 4.8 Add a 1–2 sentence note explaining the precision/coverage trade-off implied by the `min_results` floor (D7)

## 5. Section 3.4.2: Image-to-Image Pipeline

- [x] 5.1 Reuse the PATH 2 image-search TikZ flow diagram from `agent_v2_path2.tex`
- [x] 5.2 **Correct vector dimension**: replace any "512-dim vector" labels in the reused TikZ with "768-d" before pasting (per Risk in design.md)
- [x] 5.3 Reuse algorithm `EncodeQueryImage`, add Source: `search/image_query_engine.py`
- [x] 5.4 Reuse algorithm `SearchByImageBytes` (drop original Python wrapper; keep the algorithmic body)
- [x] 5.5 Author algorithm `ValidatePNGUpload` — size cap, MIME check, PIL integrity verification. Cite `api/main.py:_validate_path2_png_upload`
- [x] 5.6 Add brief endpoint contract table for the PATH 2 routes (path, method, request, response) — replace any Python endpoint listings
- [x] 5.7 Reuse the PATH 1 vs PATH 2 comparison table (input / parsing / encoding / search / reranking / speed / use case / isolation) from `agent_v2_path2.tex`
- [x] 5.8 Add a single sentence noting the `ENABLE_PATH2_IMAGE_SEARCH` feature flag (CLAUDE.md gotcha)

## 6. Section 3.5: Tool-Augmented Execution and Deterministic Logic

- [x] 6.1 Reuse algorithm `OrchestrateStream` (Step 4 of the pipeline), add Source: `agent/fashion_agent.py:_orchestrate_stream`
- [x] 6.2 Reuse the routing-decisions list/table for `out_of_scope`, `product_select`, `view_selections`, `text_search`/`outfit_request`/`follow_up`, plus the confidence-< 0.6 fallback
- [x] 6.3 Author algorithm `ResolveSearchQuery` — confidence-gate / readiness-gate decision tree. Cite `agent/fashion_agent.py:_resolve_search_query`
- [x] 6.4 Author algorithm `FilterByGender` — consumes recorded session gender, returns filtered product list. Cite `agent/fashion_agent.py:_filter_by_gender`
- [x] 6.5 Author algorithm `SynthesizeResponse` (Step 5) — gender-context injection, JSON parse with fallback. Cite `agent/fashion_agent.py:_synthesize_response`
- [x] 6.6 Verify zero Python listings remain in 3.5

## 7. Section 3.6: Evaluation Framework and Experimental Setup

- [x] 7.1 Author opening prose: "this section defines the protocol, not the results"
- [x] 7.2 Reuse the metric definitions table (Recall@5, MRR, Hit Rate@5, Latency P95, Faithfulness, Token Cost), with formulas where applicable
- [x] 7.3 Reuse the token-aggregation equation from `evaluation_conclusion.tex`
- [x] 7.4 Reuse the CartAddRate / WillBuyRate / ConversionRate equations
- [x] 7.5 Reuse the inclusion/exclusion rules (time window, missing-field exclusion, dedup, original vs. post-filter cohort sizes)
- [x] 7.6 Reuse the data-validity checks table (missingness, consistency, duplicate events, sample balance)
- [x] 7.7 Author the experimental matrix: query clarity (clear / partial / ambiguous) × query type (text-search / outfit-request / follow-up / image-upload) × orchestration mode (direct / agentic). Note cells deferred to future work
- [x] 7.8 Strip any sentence that reports a numeric result (e.g., "Recall@5 = 0.81"); keep only protocol descriptions

## 8. Verification (acceptance gates from the spec)

- [x] 8.1 `grep -c '\\begin{lstlisting}' methodology.tex` after 3.1 returns 0 (no code listings in 3.2–3.6)
- [x] 8.2 Every `\begin{algorithm}` introduced in 3.2–3.6 is followed by a `\textit{Source: \texttt{...}}` line that points to a real file under `fashion_agent/`
- [x] 8.3 Diff Section 3.1 against `git show HEAD:fashion_agent/documents/Report_thesis_2/chapters/methodology.tex` — only whitespace at section boundaries should differ
- [x] 8.4 The PATH 2 TikZ figure shows "768-d" (not 512); grep the new content for `512` to confirm
- [x] 8.5 The HybridSearch algorithm explicitly mentions: 7 stages, BM25=2.5, img=1.0, text=1.5, k=60, soft filter, BGE rerank blend `0.7/0.3`, `MIN_SCORE_THRESHOLD = 0.25`, `min_results = 1`
- [x] 8.6 The IsQueryReady algorithm includes weights {category=4, color=3, occasion=3, style=2} and threshold 0.75
- [x] 8.7 Section 3.3 names all six extraction slots plus `selected_numbers`
- [x] 8.8 Section 3.6 contains zero specific Recall/MRR/Hit-Rate values and no v1.0-vs-v2.0 comparison tables
- [x] 8.9 `latexmk -pdf Report_thesis_2/main.tex` (run by user) compiles without missing-environment / undefined-citation errors related to the new content
- [x] 8.10 Re-run `openspec validate complete-methodology-thesis-v2 --strict` after edits and confirm no validation errors

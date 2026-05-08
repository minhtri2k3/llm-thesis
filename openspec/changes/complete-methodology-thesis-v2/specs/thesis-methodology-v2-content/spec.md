## ADDED Requirements

### Requirement: Section 3.1 Preserved Verbatim

The system SHALL leave the existing content of Section 3.1 (Research Design and Proposal System Architecture, including subsections 3.1.1 and 3.1.2 and the workflow TikZ figure) unchanged.

#### Scenario: 3.1 unchanged after edit
- **WHEN** the methodology completion is applied
- **THEN** lines 5 through 66 of the original `methodology.tex` (covering `\section{Research Design...}` through the closing of `fig:workflow_v2`) are byte-identical to before, except for trivial whitespace at section boundaries

### Requirement: Section 3.2 Data Acquisition and Knowledge Base Construction

The system SHALL populate Section 3.2 with subsections covering: dataset description, data cleaning and noise filtering, multimodal caption generation, color enrichment, PostgreSQL schema, and Qdrant multi-vector index construction. Every Python and SQL listing SHALL be replaced with an algorithm environment or a LaTeX schema table.

#### Scenario: Dataset table is reused
- **WHEN** Section 3.2 is rendered
- **THEN** the four-column dataset description table from `Report_thesis/chapters/data_preprocessing.tex` (image / label / color / caption) appears, with no SQL or Python.

#### Scenario: PostgreSQL schema is presented as a table
- **WHEN** the PostgreSQL schema subsection is rendered
- **THEN** it presents columns of `fashion_items`, `sessions`, `session_messages`, and `fashion_item_enrichment` as LaTeX tables (Column / Type / Description) and contains zero `\begin{lstlisting}[language=sql]` blocks

#### Scenario: Multimodal caption pipeline is algorithmic
- **WHEN** caption generation is described
- **THEN** the chapter contains an `algorithm` environment named `GenerateSearchCaption` (or equivalent) with a "Source: pre_processing/processing_data.py" caption note and no Python listing

#### Scenario: Index build pipeline is algorithmic
- **WHEN** Qdrant index construction is described
- **THEN** the chapter contains an `algorithm` environment named `BuildMultiVectorIndex` (or equivalent) covering image-vector encoding, text-vector encoding, BM25 content composition, and Qdrant upsert with named vectors and JSON payload

### Requirement: Section 3.3 The Agentic Reasoning Engine

The system SHALL populate Section 3.3 with subsections covering: intent classification with six-slot extraction, short-term memory via TTLCache, slot-readiness clarification gate, deterministic clarification templates, and long-term memory via PostgreSQL JSONB.

#### Scenario: Six-slot extraction documented
- **WHEN** intent classification is described
- **THEN** the chapter names all six extraction slots (`category`, `color`, `fabric`, `fit`, `construction`, `aesthetic`) and the `selected_numbers` field, matching `agent/intent_classifier.py:ExtractedSlots`

#### Scenario: 7-intent table reused
- **WHEN** the intent table is rendered
- **THEN** the seven-row table (text_search, outfit_request, follow_up, product_select, view_selections, out_of_scope, unclear) from `agent_v2_path1.tex` appears with conditions and actions

#### Scenario: Slot-readiness algorithm uses ranked weights
- **WHEN** the clarification gate is described
- **THEN** the chapter includes the IsQueryReady algorithm with weights {category=4, color=3, occasion=3, style=2} and references the search-confidence threshold of 0.75

#### Scenario: TTLCache short-term memory is described
- **WHEN** session memory is discussed
- **THEN** the chapter explains `_session_ranked_slots`, `_session_last_results`, and `_session_pending_selection` with TTL=1800s and includes the MergeSessionSlots algorithm

#### Scenario: Long-term memory is algorithmic, not Python
- **WHEN** PostgreSQL JSONB writes are described
- **THEN** the chapter contains algorithms `LogQueryHistory`, `AddLikedItem`, and `GetPreferences` with source-file citations and contains zero `\begin{lstlisting}[language=Python]` blocks for memory operations

### Requirement: Section 3.4 Multi-Modal Retrieval Pipelines

The system SHALL populate Section 3.4 with subsection 3.4.1 (text-to-image) and subsection 3.4.2 (image-to-image). Section 3.4 SHALL include the FashionSigLIP cross-modal motivation, BM25 + vector retrieval, RRF fusion, soft relevance filtering, and BGE rerank with score blending.

#### Scenario: HybridSearch documents all 7 stages
- **WHEN** the text-to-image pipeline is described
- **THEN** the chapter includes a HybridSearch algorithm covering: query expansion gate (short-query threshold), per-query BM25 retrieval, per-query image-vector retrieval, per-query text-vector retrieval, dedup-merge, three-way RRF with weights (BM25=2.5, img=1.0, text=1.5, k=60), filter-aware scoring or RapidFuzz soft filter, BGE rerank with 0.7×reranker + 0.3×RRF blend, and minimum-score threshold with `min_results` floor

#### Scenario: RRF equation reused
- **WHEN** the fusion stage is described
- **THEN** the chapter shows the RRF equation `score(d) = sum_r w_r/(k + rank_r(d) + 1)` with the equation label preserved for cross-reference

#### Scenario: PATH 2 diagram has correct vector dimension
- **WHEN** the image-to-image pipeline is described
- **THEN** the reused TikZ flow diagram lists the FashionSigLIP encoder output as 768-d (not 512-d); any inherited "512-dim vector" labels are corrected

#### Scenario: PATH 1 vs PATH 2 comparison table reused
- **WHEN** Section 3.4 closes
- **THEN** the comparison table from `agent_v2_path2.tex` (input / parsing / encoding / search method / reranking / speed / use case / isolation) appears

#### Scenario: ValidatePNGUpload is algorithmic
- **WHEN** PNG upload validation is described in 3.4.2
- **THEN** the chapter contains a ValidatePNGUpload algorithm with size cap, MIME check, and PIL integrity verification, and contains zero Python listings

### Requirement: Section 3.5 Tool-Augmented Execution and Deterministic Logic

The system SHALL populate Section 3.5 with subsections describing: direct routing orchestration (Step 4 of the 5-step pipeline), gender-aware post-filtering, and LLM synthesis (Step 5).

#### Scenario: OrchestrateStream algorithm reused
- **WHEN** routing is described
- **THEN** the OrchestrateStream algorithm from `agent_v2_path1.tex` is reused with a "Source: agent/fashion_agent.py" citation

#### Scenario: Routing decisions table reused
- **WHEN** routing branches are listed
- **THEN** the bullet list of routing decisions for `out_of_scope`, `product_select`, `view_selections`, `text_search`/`outfit_request`/`follow_up`, and the confidence-< 0.6 fallback is preserved as a table or list

#### Scenario: Synthesis is algorithmic
- **WHEN** LLM synthesis is described
- **THEN** the chapter contains a SynthesizeResponse algorithm reflecting the gender-context injection and JSON parse with fallback, and contains zero Python listings

#### Scenario: Gender filter has its own algorithm
- **WHEN** gender filtering is described
- **THEN** the chapter contains a FilterByGender algorithm (or equivalent) that consumes the recorded session gender and returns a filtered product list

### Requirement: Section 3.6 Evaluation Framework and Experimental Setup

The system SHALL populate Section 3.6 with metric definitions, cohort and inclusion-exclusion rules, data-validity checks, and the experimental matrix. Section 3.6 SHALL NOT report empirical numbers (those belong in the Results chapter).

#### Scenario: Metric definitions
- **WHEN** Section 3.6 enumerates metrics
- **THEN** it defines Recall@5, MRR, Hit Rate@5, Latency P95, Faithfulness, and Token Cost (input+output) with formulas where applicable

#### Scenario: Cohort and validity rules
- **WHEN** experimental setup is described
- **THEN** the chapter includes the inclusion-exclusion rules (time window, missing-field exclusion, dedup, original-vs-post-filter cohort sizes) and the data-validity checks table (missingness, consistency, duplicate events, sample balance)

#### Scenario: No empirical numbers
- **WHEN** Section 3.6 is rendered
- **THEN** the chapter contains zero RAG-v1.0-vs-Agent-v2.0 result tables and no specific Recall/MRR/Hit-Rate values; only the *protocol* for measuring them appears

#### Scenario: Experimental matrix
- **WHEN** the evaluation design is described
- **THEN** the chapter declares the experimental matrix: query clarity levels (clear / partial / ambiguous), query types (text-search / outfit-request / follow-up / image-upload), and orchestration mode (direct / agentic) — even if some cells are deferred to future work

### Requirement: Algorithm Source Citations

Every `algorithm` environment in Sections 3.2 through 3.6 SHALL carry a small in-document note identifying the source module (e.g., `\textit{Source: \texttt{search/search\_engine.py}}`) immediately following the algorithm caption.

#### Scenario: Every new algorithm has a source citation
- **WHEN** any algorithm is rendered in Sections 3.2–3.6
- **THEN** an italicised "Source: <path>" line follows its caption, naming a real file under `fashion_agent/`

### Requirement: No Code Listings in Methodology

Sections 3.2 through 3.6 SHALL contain zero `\begin{lstlisting}` environments — Python, SQL, or otherwise. All code-shaped content is rewritten as algorithms or schema tables.

#### Scenario: No lstlisting blocks
- **WHEN** the rendered methodology is searched for `\begin{lstlisting}`
- **THEN** the count of matches in Sections 3.2–3.6 is zero

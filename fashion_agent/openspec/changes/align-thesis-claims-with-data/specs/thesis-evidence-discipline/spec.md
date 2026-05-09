## ADDED Requirements

### Requirement: Every empirical claim in the thesis SHALL trace to a named data source

Every numeric, statistical, or comparative claim asserted in `chapters/methodology.tex` (Chapter 3) and `chapters/result.tex` (Chapter 5) SHALL identify, in the surrounding text or in the §5.1 evidence-source table, the exact source from which the value was computed. The acceptable sources are:

- a PostgreSQL table or view captured by the deployed system (for example `user_sessions`, `llm_token_usage`, `session_token_summary`, `mode_cost_summary`, `product_impressions`, `product_clicks`, `selected_items`, `cart_removals`, `product_intents`, `user_orders`, `user_ratings`, `fashion_items`, `fashion_item_enrichment`, `fashion_processing_logs`, `session_path_funnel_summary`);
- the catalog of products in Qdrant (`fashion_products` collection).

Any claim that cannot be supported by one of these sources SHALL be removed from Chapter 3 and Chapter 5 and added to the Limitations & Future Work subsection of `conclusion.tex` with an explicit future-work hook.

#### Scenario: Cohort size is reported with its source
- **WHEN** §5.2 of `result.tex` reports the cohort size for the evaluation window
- **THEN** the surrounding text identifies `user_sessions` as the source table and the inclusion filter (window range, presence of at least one row in `product_impressions`, etc.) is stated in prose

#### Scenario: A claim with no measurable source is moved to Limitations
- **WHEN** a draft sentence asserts that the seven-stage retrieval pipeline outperforms a single-signal baseline
- **AND** no labelled retrieval gold set exists in the repository at the time of writing
- **THEN** the sentence SHALL NOT appear in `methodology.tex` or `result.tex`
- **AND** an entry SHALL be added to the Limitations subsection of `conclusion.tex` with the future-work hook "construct a labelled gold set and run an ablation across the seven stages"

### Requirement: result.tex SHALL follow the §5.1–§5.6 six-section outline

`chapters/result.tex` SHALL be organised into exactly the following six sections, in order, each anchored to a single, named data source:

- §5.1 Evaluation framework — preserves the existing definitions, validity gates, and cohort rules from the current `result.tex`.
- §5.2 Cohort and integrity — sourced from `user_sessions` filtered by the declared window, with sample-balance counts per `path_mode` and funnel-integrity flags computed from `_evaluate_funnel_integrity` in `agent/memory.py`.
- §5.3 Knowledge-base quality — sourced from `fashion_items` joined with `fashion_item_enrichment` and from `fashion_processing_logs`. Reports enrichment coverage percentages for `caption` and `color`, the caption-length distribution against the 30–40-word target stated in §3.2, and processing-log success/skip/error counts.
- §5.4 LLM call discipline — sourced from `llm_token_usage` and the views `session_token_summary` and `mode_cost_summary`. Reports the distribution of `call_name` per turn, the histogram of LLM calls per turn, average input/output tokens per turn, and average USD cost per turn.
- §5.5 Implicit relevance from user behaviour — sourced from `product_impressions`, `product_clicks`, `selected_items`, `cart_removals`, `product_intents`, and the view `session_path_funnel_summary`. Reports the funnel impressions → clicks → cart_adds → will_buy (orders are excluded as a quality metric and reported only as a session-end signal in §5.2), the position-of-cart-add distribution (using `product_impressions.position` joined to `selected_items` when `selected_items.position` fidelity is below the threshold defined in §5.5.1), and the cart-removal rate. PATH 1 is the primary funnel; PATH 2 is reported as a brief secondary table when N is non-zero.
- §5.6 Subjective quality — sourced from `user_ratings`. Reports the distribution of `rating_overall`, `rating_suggestions`, and `rating_conversation` as mean ± standard deviation with N reported, and a manual coding of free-text themes from `user_ratings.feedback` and `product_intents.reason` when those rows are non-empty.

System latency, concurrency, and stress-test results SHALL not appear as a section of `result.tex`. Their absence is captured by the Limitations subsection of `conclusion.tex` rather than by a section that promises and then defers numbers.

#### Scenario: A draft of result.tex is reviewed for outline conformance
- **WHEN** a reviewer reads `chapters/result.tex` after this change is applied
- **THEN** the reviewer finds exactly six numbered sections in the order §5.1, §5.2, §5.3, §5.4, §5.5, §5.6
- **AND** each section opens with a sentence that names its data source

#### Scenario: A reviewer asks where a number came from
- **WHEN** the reviewer points at any percentage, count, or rate in §5.2 through §5.6
- **THEN** the source table is identifiable from the surrounding text or from the §5.1 evidence-source table without consulting code

#### Scenario: result.tex is reviewed for absent latency / stress section
- **WHEN** a reviewer reads `chapters/result.tex` after this change is applied
- **THEN** no section reports latency P50/P95/P99, throughput, concurrency, or stress-test results
- **AND** the Limitations subsection of `conclusion.tex` names the deferred bench explicitly

### Requirement: Chapter 3 §3.4 SHALL not assert empirical superiority without supporting evidence

The text of `methodology.tex` §3.4 (Multi-Modal Retrieval Pipelines) SHALL describe the design and mechanism of the seven-stage hybrid pipeline (PATH 1) and the single-stage cosine pipeline (PATH 2) without asserting that one configuration outperforms another, since no labelled retrieval gold set exists at the time of writing.

#### Scenario: §3.4 is read after the change is applied
- **WHEN** a reader reads `methodology.tex` §3.4 after this change is applied
- **THEN** the reader finds no sentence claiming that the hybrid pipeline beats, outperforms, or improves over a single-signal baseline
- **AND** the algorithms (cosine similarity, RRF, query expansion, BGE rerank) and the table comparing PATH 1 and PATH 2 mechanisms are preserved

#### Scenario: An ablation result is later produced
- **WHEN** a future change produces an ablation across the seven stages with a labelled gold set
- **THEN** the empirical claim about superiority MAY be reintroduced, in a new chapter or section, anchored to that experiment

### Requirement: §3.6 metric definitions SHALL include only metrics with data available

The metric definitions table in `methodology.tex` §3.6 SHALL contain only metrics whose values can be computed from the data sources enumerated in this spec. Specifically, Recall@5, MRR, Hit Rate@5, Faithfulness, and Latency P95 SHALL be removed from this table and from any "RAG v1.0 vs Agent v2.0" comparison table currently present in `result.tex`. Latency P95 is removed because no concurrency or stress benchmark is run under this change.

#### Scenario: §3.6 metric table is reviewed
- **WHEN** a reviewer reads the metric definitions table in `methodology.tex` §3.6 after this change is applied
- **THEN** the table contains rows for Token Cost and the Behaviour-funnel metrics (CartAddRate, WillBuyRate, ConversionRate)
- **AND** the table contains no rows for Recall@5, MRR, Hit Rate@5, Faithfulness, or Latency P95

#### Scenario: result.tex is reviewed for stale comparison tables
- **WHEN** a reviewer reads `chapters/result.tex` after this change is applied
- **THEN** no table compares "RAG v1.0" with "Agent v2.0" using Recall@5, MRR, Hit Rate@5, Faithfulness, or Latency thresholds

### Requirement: §3.6 experimental matrix SHALL drop the orchestration-mode factor

The experimental matrix in `methodology.tex` §3.6 SHALL drop the `orchestration mode` factor, since orchestration modes B (Gemini → GPT) and C (GPT → Claude) were never enabled in the deployment that produced the cohort. The remaining factors (query clarity, query type) SHALL be retained as they describe how the live default mode is exercised.

#### Scenario: Experimental matrix is reviewed
- **WHEN** a reviewer reads the experimental matrix in `methodology.tex` §3.6 after this change is applied
- **THEN** no row, column, or factor references "orchestration mode", "direct vs agentic", or "Mode A / Mode B / Mode C"
- **AND** the remaining factors describe only behaviours that the deployed Mode A actually exercises

### Requirement: The gender-hint A/B claim SHALL be removed from thesis text

The thesis text (Chapter 3, Chapter 5) SHALL not assert that enabling the gender hint produces a higher Gender-Appropriate Selection (GAS) score than disabling it, because the control arm of the A/B is structurally empty: `agent/memory.py:create_session()` defaults `gender_hint_enabled` to `TRUE` whenever a non-null `gender` is supplied. The corresponding analytics endpoint (`api/analytics.py:get_gender_ab`) and the database columns (`user_sessions.gender`, `user_sessions.gender_hint_enabled`) MAY remain in the codebase to preserve future research optionality.

#### Scenario: GAS is no longer cited
- **WHEN** a reviewer searches `methodology.tex` and `result.tex` for "GAS", "Gender-Appropriate Selection", "gender_hint_enabled", or "gender A/B"
- **THEN** no surviving sentence asserts an empirical contrast between the hint-on and hint-off groups

#### Scenario: The endpoint and schema are not removed
- **WHEN** the thesis change is applied
- **THEN** `api/analytics.py:get_gender_ab` is unchanged
- **AND** the columns `user_sessions.gender` and `user_sessions.gender_hint_enabled` remain in the schema as documented in `agent/memory.py:init_memory_tables`

### Requirement: A Limitations & Future Work subsection SHALL exist in conclusion.tex

`chapters/conclusion.tex` SHALL contain a subsection titled "Limitations and Future Work" that captures every claim removed from Chapter 3 or Chapter 5 by this change. The subsection SHALL list at least the following six entries, each as a paragraph with a future-work hook:

- six-slot extraction is not persisted to PostgreSQL — only `query_history.filters` (color, category, style) is saved, while the remaining slots (fabric, fit, construction, aesthetic) live in the in-memory TTLCache only;
- no labelled retrieval gold set exists in the repository, so Recall@5, MRR, Hit Rate@5, and Faithfulness cannot be computed;
- the gender-hint A/B has no control arm because `gender_hint_enabled` defaults to `TRUE` for every gendered session;
- per-call LLM `duration_ms` is not stored in `llm_token_usage`, so retrospective per-call latency aggregates are not possible from the deployed cohort;
- orchestration modes B and C scaffolded in `agent/agentic_orchestrator.py` were never enabled in production; comparison data is therefore not available;
- no concurrency or stress benchmark has been run; therefore the thesis does not report system latency under load. The future-work hook is to design and execute a locust-based bench against `POST /api/chat/stream` once a measurement window is allocated.

#### Scenario: Limitations subsection is reviewed
- **WHEN** a reviewer reads `conclusion.tex` after this change is applied
- **THEN** a subsection titled "Limitations and Future Work" exists
- **AND** it contains paragraphs covering the six entries listed above
- **AND** each paragraph names a concrete future-work direction (for example "construct a labelled gold set and run an ablation", "add a `duration_ms` column and populate it from the existing `thinking_end` timing", "design and execute a locust-based bench against `/api/chat/stream`")

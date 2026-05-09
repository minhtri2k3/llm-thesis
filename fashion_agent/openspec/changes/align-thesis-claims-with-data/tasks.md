## 1. Pre-flight inputs

- [x] 1.1 Elicit the cohort window `[t_start, t_end]` from the author and record it in this task list before any thesis edit begins — **OPEN window; data freeze = 2026-05-09; earliest session = 2026-04-20; latest session = 2026-05-08; total = 53 sessions**
- [x] 1.2 Run the sanity-check query `SELECT position, COUNT(*) FROM selected_items WHERE path_mode = 'path1' GROUP BY position ORDER BY position` against the running PostgreSQL and record the distribution — **{0:4, 1:5, 2:3, 3:2, 4:2, 5:3, 6:2}; total=21; `position=0` share = 19.05%**
- [x] 1.3 Decide the §5.5 position-histogram source from 1.2: if `position = 0` exceeds 20% of rows, source from `selected_items ⨝ product_impressions`; otherwise source from `selected_items.position` — **19.05% ≤ 20% → use `selected_items.position` directly; flag borderline in §5.5 prose**
- [x] 1.4 Run cohort-count queries within the window: total `user_sessions`, sessions with at least one `product_impressions` row, sessions with at least one `user_ratings` row, sessions per `path_mode`. Record the four numbers in §5.2's draft — **53 / 25 / 9 / path1=27 path2=7 (sessions ending in order = 8)**
- [x] 1.5 Run enrichment-coverage queries: count of `fashion_items`, count of `fashion_item_enrichment` rows with non-empty `caption`, count with non-empty `color`, distribution of `fashion_processing_logs.status`. Record numbers in §5.3's draft — **5096 items; 100% caption coverage; 100% color coverage; avg caption 34.9 words (range 17–48); processing_logs empty**
- [x] 1.6 Run LLM-call queries: `SELECT call_name, COUNT(*) FROM llm_token_usage GROUP BY call_name`, plus average input and output tokens per turn from `session_token_summary`, plus average USD per turn from `mode_cost_summary`. Record numbers in §5.4's draft — **155 intent + 60 synthesis + 0 expansion; per-turn calls ∈ {1, 2}; avg USD/turn = $0.000131**
- [x] 1.7 Run funnel queries from `session_path_funnel_summary` filtered to the window. Record per-step counts and rates in §5.5's draft — **PATH 1: 254 imp → 81 clk (CTR 31.9%) → 21 cart (8.3% of imp) → 2 will_buy → 9 orders; PATH 2: 42 imp → 6 → 2 → 0 → 0; cart_removals = 0**
- [x] 1.8 Run rating queries: distribution of `rating_overall`, `rating_suggestions`, `rating_conversation` plus N. Record numbers in §5.6's draft — **N=9; overall 4.56±0.53; suggestions 4.67±0.50; conversation 4.22±0.83; rating_overall = {4:4, 5:5}; feedback non-empty 8/9; product_intents.reason non-empty 0/3**

## 2. Methodology (Chapter 3) edits

- [x] 2.1 Soften §3.4 introduction prose to remove any sentence implying empirical superiority of the seven-stage hybrid pipeline over single-signal baselines; preserve all algorithm boxes (cosine similarity, RRF, query expansion, BGE rerank) and the PATH 1 vs PATH 2 mechanism comparison table — already descriptive, no superiority phrasing found
- [x] 2.2 Remove the rows for Recall@5, MRR, Hit Rate@5, Faithfulness, and Latency P95 from the metric definitions table in §3.6 — replaced with Cart-add rate, Will-buy rate, LLM-call discipline rows
- [x] 2.3 Remove any "RAG v1.0 vs Agent v2.0" comparison table or threshold callout that cites Recall@5 / MRR / Hit Rate@5 / Faithfulness / Latency from `methodology.tex` and `result.tex` — `result.tex` was rewritten from scratch; methodology never had such a table
- [x] 2.4 Remove the orchestration-mode factor (direct / agentic) from the §3.6 experimental matrix; keep the query-clarity and query-type factors
- [x] 2.5 Remove every reference to `gender_hint_enabled`, GAS, Gender-Appropriate Selection, or gender A/B from `methodology.tex` — only mention is in the "Sample balance" check description, replaced with `path_mode`-only language
- [x] 2.6 Confirm by `grep` that no surviving sentence in `methodology.tex` cites Recall@5, MRR, Hit Rate@5, Faithfulness, "Latency P95", GAS, gender_hint_enabled, "outperforms", "beats", or "improves over" — verified clean

## 3. Result chapter (Chapter 5) restructure

- [x] 3.1 Preserve the existing §5.1 evaluation framework subsections (definitions, validity gates, cohort rules) verbatim; renumber if necessary — kept and reframed for the open-window cohort with data-freeze note
- [x] 3.2 Write §5.2 Cohort and integrity using the numbers from 1.4, with sample-balance counts per `path_mode` and a funnel-integrity flag tally computed from `_evaluate_funnel_integrity`
- [x] 3.3 Write §5.3 Knowledge-base quality using the numbers from 1.5, including caption coverage, color coverage, the caption-length distribution against the 30–40-word target stated in §3.2, and the processing-log status counts
- [x] 3.4 Write §5.4 LLM call discipline using the numbers from 1.6, including the histogram of LLM calls per turn and the prose argument that the deployed pipeline calls the LLM 1–2 times per turn
- [x] 3.5 Write §5.5 Implicit relevance from user behaviour using the numbers from 1.7, with the position-of-cart-add histogram sourced according to 1.3, the cart-removal rate, and a brief secondary table for PATH 2 only when its N is non-zero
- [x] 3.6 Write §5.6 Subjective quality using the numbers from 1.8, reporting mean ± standard deviation with N, and a manual coding of free-text themes from `user_ratings.feedback` and `product_intents.reason` when those rows are non-empty — N=9 too small for thematic table; reported as anecdotal
- [x] 3.7 Remove every prior `result.tex` table or sentence that references GAS, gender-A/B analytics, Recall@5 / MRR / Hit Rate@5 thresholds, Latency P95 thresholds, or PATH 1 vs PATH 2 funnel comparisons
- [x] 3.8 Confirm by review that `result.tex` has exactly six numbered sections in the order §5.1 through §5.6, and that each section opens with a sentence that names its data source — verified six sections via `grep -cE "^\\\\section"`
- [x] 3.9 Confirm that no section of `result.tex` reports latency, concurrency, throughput, or stress-test results

## 4. Conclusion (Limitations and Future Work)

- [x] 4.1 Add a subsection titled "Limitations and Future Work" to `conclusion.tex`
- [x] 4.2 Add a paragraph for "six-slot extraction is not persisted to PostgreSQL" with the future-work hook of adding a `turn_slots` JSONB column to `conversation_history` and collecting a fresh window
- [x] 4.3 Add a paragraph for "no labelled retrieval gold set" with the future-work hook of constructing a 50–200 query gold set and running an ablation across the seven stages
- [x] 4.4 Add a paragraph for "the gender-hint A/B has no control arm" with the future-work hook of randomising `gender_hint_enabled` from the frontend and collecting a fresh window
- [x] 4.5 Add a paragraph for "per-call LLM `duration_ms` is not stored in PostgreSQL" with the future-work hook of adding a `duration_ms` column to `llm_token_usage` and populating it from the existing `thinking_end` timing
- [x] 4.6 Add a paragraph for "orchestration modes B and C are not deployed" with the future-work hook of wiring `agent/agentic_orchestrator.py` into the live router behind a feature flag and randomising mode assignment
- [x] 4.7 Add a paragraph for "no concurrency or stress benchmark has been run" with the future-work hook of designing and executing a locust-based bench against `POST /api/chat/stream` with a concurrency sweep at {1, 5, 10, 20, 50} virtual users once a measurement window is allocated
- [ ] 4.8 Optional: add a paragraph for "no baseline against RAG v1.0" if the author wishes to cite literature baselines explicitly — skipped (optional)
- [ ] 4.9 Optional: add a paragraph for "PATH 2 is not evaluated in depth" if the author wishes to acknowledge the visual-similarity-only scope — skipped (optional)

## 5. Verification before the change is closed

- [x] 5.1 Run `openspec validate align-thesis-claims-with-data --strict` and confirm it passes — passed
- [x] 5.2 Re-`grep` `methodology.tex`, `result.tex`, and `conclusion.tex` for the forbidden tokens listed in 2.6 and confirm no occurrences remain — only matches are in `conclusion.tex` Limitations paragraphs where the deferred items are intentionally named (e.g. "Recall@5 ... not reported in this thesis"); no body sentence in methodology or result asserts any of these
- [x] 5.3 Confirm that `api/analytics.py:get_gender_ab` is unchanged and that the `user_sessions.gender` and `user_sessions.gender_hint_enabled` columns remain in `agent/memory.py:init_memory_tables` — 10 references to `get_gender_ab` / `MALE_CATEGORIES` / `FEMALE_CATEGORIES` still in `api/analytics.py`; `gender TEXT` and `gender_hint_enabled BOOLEAN` still in `agent/memory.py`
- [x] 5.4 Confirm that no PostgreSQL migration is included in this change — no new `.sql` files created
- [ ] 5.5 Run `pdflatex` (or the project's equivalent) to confirm `Report_thesis_2` builds without errors after the chapter edits — `pdflatex` is not installed in this environment; author SHOULD run locally before committing

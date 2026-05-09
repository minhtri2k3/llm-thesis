## Why

Chapter 5 of the thesis currently states an evaluation framework but reports no empirical numbers, while several Chapter 3 claims (hybrid retrieval beats single-signal baselines; gender-hint A/B improves Gender-Appropriate Selection; Recall@5 / MRR / Hit Rate@5 / Faithfulness over a labelled gold set) cannot be supported by data the deployed system actually captures. Writing those numbers would be fabrication; staying silent leaves the thesis defenceless at viva. This change reconciles thesis text with provable evidence: every empirical claim in the rewritten Chapter 5 traces to a query against existing telemetry, and every dropped claim is captured in a Limitations section in the Conclusion with a future-work hook.

## What Changes

- **Restructure `result.tex` into six sections (§5.1–§5.6)**, each anchored to a single, named data source we can produce today: cohort integrity, knowledge-base quality, LLM call discipline, implicit relevance from user behaviour, and subjective quality from `rating_overall`. The existing `result.tex` framework subsections (definitions, validity gates) are preserved as §5.1.
- **Soften Chapter 3 §3.4 (Multi-Modal Retrieval Pipelines)** to remove any phrasing that asserts empirical superiority of the seven-stage hybrid pipeline over single-signal baselines. The mechanism description and algorithms stay; the implicit "beats baselines" claim is removed because no labelled gold set or ablation exists.
- **Drop Recall@5 / MRR / Hit Rate@5 / Faithfulness rows** from the §3.6 metric definitions table. Token Cost and Behaviour-Funnel definitions remain.
- **Drop the orchestration-mode factor** from the §3.6 experimental matrix — Modes B and C were never deployed in production, so any comparison is vacuous.
- **Drop the gender-hint A/B claim entirely** from the thesis text. The mechanism's control arm is empty by default (`create_session()` sets `gender_hint_enabled = TRUE` whenever gender is supplied), so a contrast cannot be computed. The `api/analytics/gender-ab` endpoint stays in code but is no longer cited.
- **No latency or stress-test section** is included in this change. System latency and concurrency measurement are deferred to future work; no locust bench is designed or executed under this proposal. Latency P95 is removed from the §3.6 metric table along with the retrieval metrics above.
- **Add a Limitations & Future Work subsection to `conclusion.tex`** capturing six deferred items, each with a future-work hook: 6-slot extraction not persisted; no labelled retrieval gold set; no control group for gender-hint A/B; per-call LLM `duration_ms` not stored in Postgres; orchestration modes B and C not deployed; no concurrency / stress benchmark has been run.
- **BREAKING (thesis-content-only)**: prior `result.tex` references to GAS, gender-A/B analytics, Recall@5 / MRR / Hit Rate@5 thresholds (e.g. the "≥0.80 MRR" target), Latency P95 thresholds, and PATH 1 vs PATH 2 funnel comparisons are removed. No runtime API or database behaviour changes.

## Capabilities

### New Capabilities

- `thesis-evidence-discipline`: The contract that every empirical claim asserted in the thesis (Chapter 3, Chapter 5) must trace to a named data source already captured by the deployed system. Claims without such a source are moved to Conclusion → Limitations with a future-work hook. Defines the §5.1–§5.6 outline, the per-section evidence source, and the rules that soften §3.4 and §3.6.

### Modified Capabilities

(none — this change does not alter the spec-level behaviour of any existing runtime capability)

## Impact

- **Thesis files**: `methodology.tex` (§3.4 wording softened, §3.6 metric definitions table trimmed, §3.6 experimental matrix simplified), `result.tex` (full restructure into §5.1–§5.6), `conclusion.tex` (new Limitations & Future Work subsection)
- **Code**: no runtime changes. The `gender-ab` analytics endpoint (`api/analytics.py:get_gender_ab`) stays in source but is no longer referenced by the thesis text. A future DDL `ALTER TABLE llm_token_usage ADD COLUMN duration_ms INT` and a future locust bench are listed as future-work hooks in Limitations, not part of this change.
- **Dependencies**: none added.
- **Open inputs to resolve before applying**: the cohort window `[t_start, t_end]` for §5.2–§5.5 / §5.6, and a one-shot sanity-check query (`SELECT position, COUNT(*) FROM selected_items WHERE path_mode='path1' GROUP BY position`) to decide whether §5.5's position histogram sources from `selected_items.position` or from a `selected_items ⨝ product_impressions` join.
- **No breaking changes** to chat, session, search, or analytics APIs. No database schema migrations.

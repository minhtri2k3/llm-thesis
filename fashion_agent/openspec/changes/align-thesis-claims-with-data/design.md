## Context

The thesis "Clothie / Fashion Agent" has three drafted chapters under `fashion_agent/documents/Report_thesis_2/chapters/`: `methodology.tex` (Chapter 3), `result.tex` (Chapter 5), and `conclusion.tex`. The current `result.tex` defines an evaluation framework but reports no observed values. The current `methodology.tex` makes (or strongly implies) several empirical claims that the deployed system cannot support from the data it captures:

- Recall@5, MRR, Hit Rate@5, and Faithfulness over a labelled query gold set — no such gold set exists in the repository.
- The seven-stage hybrid retrieval pipeline outperforms single-signal baselines — no ablation has been run.
- Enabling the gender hint produces a higher Gender-Appropriate Selection score than disabling it — `agent/memory.py:create_session` defaults `gender_hint_enabled` to `TRUE` whenever a non-null gender is supplied, so the control arm is structurally empty.
- Mode B (Gemini → GPT) and Mode C (GPT → Claude) of the agentic orchestrator have empirical comparison data — these modes were never enabled in the deployment that produced the cohort; `_get_orchestration_mode()` returns `"direct"`.
- Latency P95 under load is reported — no concurrency benchmark has been run, and no per-call `duration_ms` is persisted in `llm_token_usage`.

The runtime telemetry that the deployed system actually captures, and that this change treats as the canonical evidence base, is documented across `agent/memory.py:init_memory_tables` and `api/analytics.py`. The relevant tables and views are: `user_sessions` (including `gender`, `gender_hint_enabled`, `year_of_birth`, `preferred_model`, `ended_at`, `ended_by`), `conversation_history`, `selected_items`, `cart_removals`, `product_impressions`, `product_clicks`, `product_intents`, `user_orders`, `user_ratings` (with the 1–5 fields `rating_overall`, `rating_suggestions`, `rating_conversation`), `llm_token_usage`, `fashion_items`, `fashion_item_enrichment`, `fashion_processing_logs`, plus the views `session_token_summary`, `mode_cost_summary`, and `session_path_funnel_summary`.

Stakeholders: the thesis author (defending at viva), the supervising mentor (asks about evidence integrity), and the future researcher who will revisit the deferred experiments.

## Goals / Non-Goals

**Goals:**

- Reconcile every empirical sentence in `methodology.tex` and `result.tex` with a named data source captured by the deployed system.
- Restructure `result.tex` into a six-section outline (§5.1–§5.6) where every numeric block traces to a single data source.
- Soften `methodology.tex` §3.4 wording to remove implicit "beats single-signal baselines" claims while preserving the algorithmic description.
- Trim the §3.6 metric definitions table and experimental matrix so they describe only metrics and factors that the deployed cohort can support.
- Add a Limitations and Future Work subsection in `conclusion.tex` that captures every claim removed from the body and pairs it with a concrete future-work hook, including the deferred concurrency benchmark.

**Non-Goals:**

- This change does not design or run any latency, concurrency, or stress benchmark. The deferred bench is acknowledged in Limitations only; no protocol is specified by this change.
- This change does not modify any runtime API, database schema, or analytics endpoint. The `gender-ab` analytics endpoint and the `gender_hint_enabled` column remain in place untouched.
- This change does not construct a labelled retrieval gold set or run an ablation. Both are listed as future work.
- This change does not enable orchestration modes B or C, nor does it remove the scaffolded code in `agent/agentic_orchestrator.py`.
- This change does not rewrite `methodology.tex` §3.4 algorithm-by-algorithm; the algorithmic content is preserved and only the surrounding prose is softened.
- This change does not add any new file under `analysis/` or any benchmarking dependency to `requirements-dev.txt`.

## Decisions

### Decision 1 — Anchor every Chapter 5 section to one data source instead of one claim

**Choice.** Each of §5.2 through §5.6 is anchored to a single named PostgreSQL data source (table, view, or join), and the section's prose is restricted to numbers that fall out of that source.

**Alternative considered.** Anchor each section to a Chapter 3 claim, in the original "claim-evidence pair" structure of the prior draft of this proposal. Rejected because some claims in Chapter 3 are unsupportable; tying §5.x to a claim would force either fabrication or empty sections.

**Why this is better.** A reader can verify any reported number by going to the named table or view and running a sum or count. Reviewer questions of the form "where did this come from?" are answerable in one hop, without traversing chapter cross-references. Sections that have no data source disappear entirely, making the gap visible at the table-of-contents level.

### Decision 2 — Drop, do not defer, the unsupportable Chapter 3 claims

**Choice.** The Recall@5 / MRR / Hit Rate@5 / Faithfulness rows are removed from the §3.6 metric table; the implicit retrieval-superiority claim in §3.4 is removed; the gender-hint A/B is removed from both chapters; the orchestration-mode factor is removed from the §3.6 experimental matrix; Latency P95 is removed from the §3.6 metric table since no benchmark is run. None of these is "deferred to a future section of the same chapter" — all five go to Conclusion → Limitations and Future Work, where they are paired with a concrete future-work hook.

**Alternative considered.** Keep the metrics in §3.6 marked as "deferred" with empty cells in §5. Rejected because empty cells are a viva trap: the reader either skips them and reads the chapter as incomplete, or asks why they are empty and surfaces the same gaps that this change attempts to acknowledge openly.

**Why this is better.** Limitations are easier to defend than empty placeholders. A claim moved to Limitations is presented with its own framing ("we know we did not measure this; here is why; here is the future-work plan"), which is stronger at viva than an unfilled row in a results table.

### Decision 3 — Defer all latency and stress measurement to future work; do not include §5.6 latency in this change

**Choice.** No locust scenario, no concurrency sweep, no end-to-end latency table is produced under this change. `result.tex` therefore has six sections (§5.1–§5.6) instead of seven, with subjective quality occupying §5.6. The deferred bench is named in the Limitations subsection of `conclusion.tex` with a concrete future-work hook (design and execute a locust-based bench against `POST /api/chat/stream` once a measurement window is allocated).

**Alternative considered.** Include a §5.6 "System latency and concurrency" section with only its Methodology subsection populated, and the Results subsection marked as "deferred until the bench is executed". Rejected because a Methodology subsection with no Results is the same kind of empty placeholder rejected in Decision 2; it tempts a reviewer to ask "where are the numbers?" instead of accepting the deferral.

**Why this is better.** The chapter outline reflects exactly what was measured. Performance evidence lives in Limitations as a deliberate omission with a future-work plan, not as an unfinished section that promises and then withholds.

### Decision 4 — Use `product_impressions.position` instead of `selected_items.position` for the §5.5 position histogram if click fidelity is poor

**Choice.** Before §5.5 is drafted, run a sanity-check query (`SELECT position, COUNT(*) FROM selected_items WHERE path_mode='path1' GROUP BY position`). If the share of `position = 0` exceeds 20%, the histogram is sourced from a join `selected_items ⨝ product_impressions` on `(session_id, image_id, search_query)` taking the latest `product_impressions.position` for each cart-add. Otherwise, `selected_items.position` is used as-is.

**Alternative considered.** Always use `selected_items.position`. Rejected because `selected_items.position` is set to the position of the last user click on the image (`agent/fashion_agent.py:1142`), which falls back to `0` if the user added the item via numeric selection without clicking the card first. This makes the histogram unreliable as evidence about the reranker.

**Why this is better.** `product_impressions.position` is the rank at which the search itself displayed the item, independent of whether the user clicked the card. It is the correct denominator for "did the reranker put cart-added items near the top?".

### Decision 5 — Keep `gender-ab` analytics code; remove only thesis-text references

**Choice.** The `api/analytics.py:get_gender_ab` endpoint and the `user_sessions.gender_hint_enabled` column remain in the codebase exactly as they are today. Only thesis prose stops citing them.

**Alternative considered.** Remove the endpoint and the column to keep the codebase aligned with the thesis. Rejected because a future change may yet introduce a real control arm and run a proper A/B; the infrastructure is harmless to keep, and removing it would bloat this change with code edits unrelated to its purpose.

**Why this is better.** The change stays scoped to thesis files plus the openspec spec. Code review is trivial because no code is touched.

## Risks / Trade-offs

- **The cohort window is not yet decided** → This change cannot be applied until the author commits to a `[t_start, t_end]` for §5.2–§5.6. Mitigation: the apply step has, as its first task, to elicit the window from the author.
- **Removing the gender A/B may surprise readers who saw earlier drafts** → Reviewers expecting the gender contrast may flag its absence. Mitigation: the Limitations subsection of `conclusion.tex` names the deferred experiment explicitly so the absence is visible rather than implicit.
- **Trimming §3.6 metric definitions removes Recall@5 / MRR / Hit Rate@5 / Latency P95** → A reviewer may interpret the absence of standard retrieval and performance metrics as the thesis avoiding rigour. Mitigation: the Limitations subsection acknowledges each gap directly and pairs it with a concrete future-work hook.
- **The `product_impressions ⨝ selected_items` join may have low coverage** → If the FE did not consistently log impressions before cart-adds, the alternate position histogram is also degraded. Mitigation: the sanity-check query covers both source columns; if neither is usable, §5.5's position histogram is replaced with a text paragraph stating that the within-system rank evidence is inconclusive, and the gap is named in Limitations.
- **No latency evidence at all may concern a hardware-oriented reviewer** → The thesis loses the concurrency-sweep narrative that would have showcased engineering rigor. Mitigation: the Limitations entry frames the deferral as a deliberate scope decision and proposes the bench as the obvious next experiment, leaving a clean handoff to follow-up work.

## Migration Plan

1. The author chooses `[t_start, t_end]` for the cohort window.
2. The thesis-content edits (Chapter 3 softening, Chapter 5 restructure to six sections, Conclusion limitations) land as one commit.
3. A small sanity-check is run against the running PostgreSQL: cohort N counts in the chosen window, and the `selected_items.position` distribution. The §5.5 histogram source is decided from this output.
4. No rollback is required for thesis text — `git revert` on the commit suffices. No database or runtime change exists to roll back.

## Open Questions

- What window `[t_start, t_end]` defines the cohort? Without this, §5.2 cannot be drafted.
- Should `user_orders` (phone + address simulation) be reported at all in §5.2's session-end signal table, or omitted entirely because no real money changes hands? The current decision is to report it as a session-end count only and never to use it as a quality metric.
- Should the §5.6 manual coding of `user_ratings.feedback` and `product_intents.reason` themes be performed by the author alone, or by the author plus the supervisor? This decision affects how the qualitative evidence is presented (single-coder vs inter-rater).
- Should the future-work locust bench and the future-work DDL `ALTER TABLE llm_token_usage ADD COLUMN duration_ms INT` be scheduled as a single follow-up change after this one, or treated as independent items? The Limitations subsection names them as future work; this proposal does not commit to a sequence.

## Context

The Fashion Agent backend already logs per-turn LLM usage in `llm_token_usage` with orchestration metadata (`orchestration_mode`, `orchestrator_model`, `synthesizer_model`, `orchestrator_input_tokens`, `orchestrator_output_tokens`, `tool_calls_json`) and user behaviour signals in `user_sessions` (`liked_items`, `query_history`, `ended_by`, `gender`, `gender_hint_enabled`).

The current analytics API (`GET /api/analytics/tokens`) returns a flat summary without mode breakdown, and there is no accuracy layer at all. The thesis requires structured, reproducible evidence comparing three orchestration modes.

## Goals / Non-Goals

**Goals:**
- Expose analytics endpoints that aggregate token cost per orchestration mode with estimated USD pricing
- Compute behavioural accuracy signals (SR, SCR, QRR, GAS) from existing DB tables — no new data collection needed
- Define a Cost-Efficiency Score (CES) as the primary cross-mode comparison metric
- Provide a reproducible analysis notebook for statistical tests and chart generation
- Support the gender A/B experiment with a dedicated endpoint

**Non-Goals:**
- Real-time dashboards (batch analytics are sufficient for a thesis)
- Human-label ground truth (behavioural signals only)
- Changes to the chat or session creation APIs
- Production-grade SLAs for analytics endpoints (best-effort)

## Decisions

### D1: Extend existing analytics endpoint vs. create new ones
**Decision**: Create `GET /api/analytics/token-costs`, `GET /api/analytics/accuracy`, and `GET /api/analytics/gender-ab` as separate endpoints.

**Why**: The existing `/api/analytics/tokens` endpoint is consumed by the Flutter leaderboard. Adding mode-breakdown columns would be a breaking change. New endpoints allow independent evolution for the thesis without disrupting the production UI.

**Alternative considered**: Single `/api/analytics/report` endpoint returning everything. Rejected because it mixes operational (token counts) and research (accuracy scores) concerns, making caching and testing harder.

---

### D2: Where to compute the Behaviour Accuracy Score
**Decision**: Compute SR, SCR, QRR, GAS in SQL using window functions and aggregations. Return raw values from the API; let the notebook compute the weighted composite.

**Why**: SQL aggregation is efficient on the existing table structure. Keeping weights in the notebook (not the DB) means the researcher can adjust the formula without touching the backend — important for thesis sensitivity analysis.

**Alternative considered**: Pre-compute in Python inside the API. Rejected because it adds latency to the endpoint and makes the formula opaque to the thesis reader.

---

### D3: USD pricing — static vs. dynamic
**Decision**: Hard-code pricing as constants in `api/analytics.py` with a `PRICING` dict (model_prefix → {input_usd_per_million, output_usd_per_million}).

**Why**: Pricing changes rarely per model family. Hard-coding with a named constant makes assumptions explicit and auditable in the thesis. Environment-variable pricing adds operational complexity with no research benefit.

---

### D4: Statistical tests — in the API or notebook
**Decision**: All statistical tests (Chi-square, Kruskal-Wallis, Cliff's delta, bootstrap CI) live in the Jupyter notebook only.

**Why**: Stats tests belong in the research analysis layer, not in a production API. The API returns raw data; the notebook does science.

---

### D5: Notebook location
**Decision**: `analysis/thesis_evaluation.ipynb` at the project root (`fashion_agent/analysis/`).

**Why**: Keeps analysis separate from application code. The `analysis/` directory is already gitignored for large data files but the notebook itself is tracked. This matches standard ML research repo conventions.

---

### D6: Token cost SQL — view or ad-hoc query
**Decision**: Update the existing `session_token_summary` DB view to include orchestration columns, and also add a new `mode_cost_summary` view for the analytics endpoint.

**Why**: Views are cacheable, testable, and make the SQL portable between the API and the notebook. The notebook can query the view directly without duplicating the pricing logic.

```sql
-- New view: mode_cost_summary
CREATE OR REPLACE VIEW mode_cost_summary AS
SELECT
  ltu.orchestration_mode,
  ltu.orchestrator_model,
  ltu.synthesizer_model,
  COUNT(DISTINCT ltu.session_id)                                      AS n_sessions,
  COUNT(*)                                                            AS n_turns,
  ROUND(AVG(ltu.input_tokens + ltu.output_tokens
    + ltu.orchestrator_input_tokens + ltu.orchestrator_output_tokens)) AS avg_total_tokens,
  ROUND(AVG(jsonb_array_length(ltu.tool_calls_json)), 2)             AS avg_tool_calls,
  ROUND(AVG(
    -- Orchestrator cost
    CASE
      WHEN ltu.orchestrator_model LIKE 'gemini%'
        THEN (ltu.orchestrator_input_tokens * 0.075 + ltu.orchestrator_output_tokens * 0.30) / 1e6
      WHEN ltu.orchestrator_model LIKE 'gpt%'
        THEN (ltu.orchestrator_input_tokens * 2.50 + ltu.orchestrator_output_tokens * 10.00) / 1e6
      ELSE 0
    END
    +
    -- Synthesizer cost
    CASE
      WHEN ltu.synthesizer_model LIKE 'gemini%'
        THEN (ltu.input_tokens * 0.075 + ltu.output_tokens * 0.30) / 1e6
      WHEN ltu.synthesizer_model LIKE 'gpt%'
        THEN (ltu.input_tokens * 2.50 + ltu.output_tokens * 10.00) / 1e6
      WHEN ltu.synthesizer_model LIKE 'claude%'
        THEN (ltu.input_tokens * 3.00 + ltu.output_tokens * 15.00) / 1e6
      ELSE 0
    END
  ), 8)                                                              AS avg_usd_per_turn
FROM llm_token_usage ltu
WHERE ltu.call_name = 'synthesis'
GROUP BY ltu.orchestration_mode, ltu.orchestrator_model, ltu.synthesizer_model;
```

## Risks / Trade-offs

- **Small sample size** → Mitigation: Report bootstrap confidence intervals alongside point estimates. Minimum 30 sessions per mode before drawing conclusions. If insufficient real sessions, document an offline evaluation approach (scripted queries).

- **QRR interpretation ambiguity** — A high QRR might mean the agent is good at multi-turn refinement (feature), not bad at first-pass accuracy (bug) → Mitigation: Supplement QRR with SR measured *per first turn only* (turn_index = 1).

- **USD pricing staleness** — Model pricing changes over time → Mitigation: Name the `PRICING` dict with a `_AS_OF` version tag in the code. Pricing is only used for relative comparison across modes (all measured in the same period), so absolute accuracy matters less than consistency.

- **Gender Alignment Score requires product gender metadata** — `fashion_items` must have a `gender` column for GAS calculation → Mitigation: Check the existing schema before implementing GAS. If the column doesn't exist, fall back to category-based inference (e.g., "Dress" → female).

- **No ground-truth accuracy** — All accuracy signals are implicit (behavioural) → This is a research design choice, not a bug. The thesis should explicitly frame this as *implicit feedback evaluation*, citing RecSys literature (e.g., Joachims et al. 2005 on click models).

## Migration Plan

1. Add `mode_cost_summary` DB view via idempotent migration in `memory.py:_run_migrations()`
2. Add `api/analytics.py` with the three new endpoints
3. Register routes in `api/main.py`
4. Create `analysis/` directory with `thesis_evaluation.ipynb`
5. Add `scipy`, `pandas`, `matplotlib`, `seaborn` to `requirements-dev.txt` (not `requirements.txt`)
6. No rollback needed — all additions, no modifications to existing endpoints

## Open Questions

- Does `fashion_items` have a `gender` column? → Check before designing GAS query
- Should the notebook pull data via the API or directly via psycopg2? → Direct DB connection is simpler and more reliable for a research notebook
- Should `analysis/` be committed to git or gitignored? → Commit the `.ipynb` file (source), gitignore large CSV exports

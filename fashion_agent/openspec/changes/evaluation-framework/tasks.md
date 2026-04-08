# Tasks — evaluation-framework

## Phase 1: Database Layer

- [x] 1. Add `mode_cost_summary` DB view in `agent/memory.py` — create the view in `init_memory_tables()` that aggregates token costs by orchestration mode, model, with estimated USD pricing (per design D6 SQL)
- [x] 2. Extend `session_token_summary` view — add orchestration breakdown columns (`orchestration_mode`, `orchestrator_model`, `synthesizer_model`, `orchestrator_input_tokens`, `orchestrator_output_tokens`) to the existing view

## Phase 2: Analytics API

- [x] 3. Create `api/analytics.py` — new module with `PRICING` dict and three endpoint handler functions: `get_token_costs()`, `get_accuracy()`, `get_gender_ab()`
- [x] 4. Implement `GET /api/analytics/token-costs` — query `mode_cost_summary` view, return JSON with per-mode token counts and USD estimates, protected by admin key
- [x] 5. Implement `GET /api/analytics/accuracy` — compute SR, SCR, QRR from `user_sessions` + `llm_token_usage`, grouped by orchestration_mode and preferred_model, protected by admin key
- [x] 6. Implement `GET /api/analytics/gender-ab` — compute GAS using category-based gender inference (fashion_items has no gender column), grouped by gender_hint_enabled and orchestration_mode, protected by admin key
- [x] 7. Register new analytics routes in `api/main.py` — import and mount the three new endpoints from `api/analytics.py`

## Phase 3: Analysis Notebook

- [x] 8. Create `analysis/thesis_evaluation.ipynb` — Jupyter notebook with sections: data pull (direct DB via psycopg2), token cost analysis, behaviour accuracy (SR/SCR/QRR/GAS), CES computation, statistical tests (Chi-square, Kruskal-Wallis, bootstrap CI, Cliff's delta), and summary table + charts
- [x] 9. Create `requirements-dev.txt` — add scipy, pandas, matplotlib, seaborn, jupyter as dev-only dependencies (not in production requirements-docker.txt)

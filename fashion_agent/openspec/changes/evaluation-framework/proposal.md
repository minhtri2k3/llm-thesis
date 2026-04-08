## Why

The Fashion Agent now supports three distinct orchestration modes (Gemini-only, Gemini-orchestrated/GPT-synthesized, GPT-orchestrated/Claude-synthesized), but there is no systematic framework to measure, compare, or draw conclusions from these modes. Without a rigorous evaluation layer, the thesis cannot make evidence-based claims about whether agentic orchestration improves recommendation quality relative to its additional token cost.

## What Changes

- **Add token cost reporting API** — new endpoint aggregating per-turn token costs broken down by orchestration mode, orchestrator model, and synthesizer model, with estimated USD cost using published pricing
- **Add behavioural accuracy scoring pipeline** — compute Selection Rate (SR), Session Completion Rate (SCR), Query Refinement Rate (QRR), and Gender Alignment Score (GAS) per mode from existing `user_sessions` and `llm_token_usage` data
- **Add Cost-Efficiency Score (CES)** — composite metric combining behavioural accuracy and cost per turn into a single comparable number across modes
- **Add agentic overhead analysis** — track agentic overhead ratio, tool call diversity, and tool call efficiency for Modes B and C
- **Add analytics notebook** — Jupyter notebook (`analysis/thesis_evaluation.ipynb`) with data pull, metric calculation, statistical tests, and chart generation
- **Add gender A/B analysis endpoint** — compare Gender Alignment Score between `gender_hint_enabled=TRUE` and `FALSE` groups per mode, with statistical significance
- **Update `session_token_summary` DB view** — extend existing view to include orchestration breakdown columns

## Capabilities

### New Capabilities
- `token-cost-report`: Per-mode token and USD cost aggregation from `llm_token_usage` — covering total tokens, orchestrator tokens, synthesizer tokens, and estimated cost per turn
- `behaviour-accuracy-score`: Four-signal implicit accuracy metric computed from user behaviour (SR, SCR, QRR, GAS) combined into a weighted composite score
- `cost-efficiency-score`: Single comparable metric = BehaviourAccuracy / AvgCostPerTurn, enabling direct mode comparison for thesis conclusions
- `agentic-overhead-analysis`: Tool call diversity, efficiency, and overhead ratio analysis for agentic Modes B and C
- `gender-ab-analysis`: Statistical comparison of Gender Alignment Score between gender hint enabled/disabled groups across modes
- `thesis-analysis-notebook`: Reproducible Jupyter notebook for data pull, metric computation, hypothesis testing (Chi-square, Kruskal-Wallis, Cliff's delta), and chart generation

### Modified Capabilities
- `multi-turn-slot-merge`: Token tracking in the slot merge flow now needs to propagate `orchestration_mode` context so per-turn analytics are correctly attributed

## Impact

- **New API endpoints**: `GET /api/analytics/token-costs`, `GET /api/analytics/accuracy`, `GET /api/analytics/gender-ab`
- **New DB view update**: `session_token_summary` extended with orchestration columns
- **New file**: `analysis/thesis_evaluation.ipynb`
- **New file**: `api/analytics.py` (analytics endpoint handlers)
- **Dependencies**: `scipy`, `pandas`, `matplotlib`, `seaborn` added to dev requirements (notebook only, not runtime)
- **No breaking changes** to existing chat or session APIs

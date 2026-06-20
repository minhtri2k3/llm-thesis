## Why

The Fashion Agent thesis currently demonstrates search quality using Hit@6, which is a single metric collected from the Direct pipeline only. Without a **baseline** to compare against, the result is not academically defensible — reviewers cannot determine whether the specialized Direct pipeline outperforms a general-purpose approach, or whether Hit@6 alone reflects real retrieval quality.

This change introduces a **parallel ReAct pipeline** as a controlled baseline. Users select their pipeline at registration time; the session is tagged throughout its lifecycle. This enables systematic comparison across offline search quality metrics (Hit@K, MRR, NDCG), system efficiency metrics (latency, LLM calls, token cost), and online behavioural metrics (SR, SCR, conversion) — all segmented by pipeline.

The ReAct pipeline is implemented as a **completely separate module** (`react_agent.py`) that shares no in-memory state with the Direct pipeline (`fashion_agent.py`). The Direct pipeline is not modified. This preserves the integrity of both pipelines and makes each independently auditable.

## What Changes

- **Register screen UI** — adds a pipeline selector (Direct ⚡ vs ReAct 🔄) alongside the existing gender selector; the selection is stored on the session at creation time
- **Session schema** — `user_sessions.orchestration_mode` column (`direct` | `react`, default `direct`) tags every session and all downstream analytics rows
- **`react_agent.py` (new file)** — independent ReAct pipeline: intent classification gate → Gemini native tool-calling loop → synthesis; logs each iteration to `react_traces`
- **API routing** — `api/main.py` reads `orchestration_mode` from the session once per request and dispatches to either `fashion_agent` or `react_agent`; `fashion_agent.py` is not modified
- **New DB tables** — `react_traces` (per-iteration logging), `eval_queries` (ground truth set), `eval_results` (offline metric results)
- **New columns** — `llm_token_usage.response_latency_ms`, `llm_token_usage.llm_call_count`
- **Evaluation runner** — `evaluation/run_comparison.py` executes both pipelines against the same `eval_queries` set and populates `eval_results` for offline analysis
- **Smoke-test harness** — a tiny `test_tool.py` pilot runner exercises a short query set before the full benchmark so DB/LLM/routing issues fail fast
- **Ground truth dataset** — `evaluation/eval_queries.json` with 40 annotated queries (easy/medium/hard, EN/VI) seeded into `eval_queries` via `evaluation/seed_eval_queries.py`
- **Notebook extension** — `analysis/thesis_evaluation.ipynb` extended with Section 7 (Direct vs ReAct: offline + online + efficiency comparison)

## Capabilities

### New Capabilities

- `react-pipeline`: Independent Gemini tool-calling agent loop gated by intent classification; logs each tool-call iteration to `react_traces` for interpretability analysis
- `pipeline-selector-ui`: Register screen UI widget (same visual style as gender selector) that writes `orchestration_mode` to the session at creation time
- `offline-eval-runner`: Script that replays a fixed ground truth query set through both pipelines and records Hit@1/3/6, MRR, NDCG@6, latency, and token counts into `eval_results`
- `ground-truth-dataset`: 40 manually annotated queries across three difficulty tiers and two languages, seeded from `eval_queries.json`
- `react-trace-logging`: Per-iteration structured logging of tool name, args, result count, and duration to `react_traces` for overhead analysis
- `response-latency-tracking`: `response_latency_ms` and `llm_call_count` columns on `llm_token_usage` enable per-turn efficiency comparison between pipelines

### Unchanged Capabilities

- `fashion_agent.py` — Direct pipeline is not modified in any way
- `agentic_orchestrator.py` — `orchestrate_with_gemini()` reused as-is by `react_agent.py`
- All existing analytics endpoints and the current thesis notebook sections (1–6)

## Impact

**New files:**
- `agent/react_agent.py`
- `evaluation/run_comparison.py`
- `evaluation/seed_eval_queries.py`
- `evaluation/eval_queries.json`

**Modified files:**
- `agent/memory.py` — DB DDL additions only (idempotent `ALTER TABLE` / `CREATE TABLE IF NOT EXISTS`)
- `api/main.py` — routing dispatch + `orchestration_mode` field on `CreateSessionRequest`
- `clothie_web/lib/services/api_service.dart` — `createSession()` accepts `orchestrationMode`
- `clothie_web/lib/screens/register_screen.dart` — pipeline selector UI widget
- `analysis/thesis_evaluation.ipynb` — Section 7 added

**No breaking changes** — `orchestration_mode` defaults to `"direct"` everywhere; existing sessions and API callers are unaffected.

**Stability guarantee** — benchmark tooling is isolated from the production chat path. The full run is always preceded by an idempotent seed step and a pilot smoke test, and benchmark sessions are created fresh per query to avoid cache/history bleed.

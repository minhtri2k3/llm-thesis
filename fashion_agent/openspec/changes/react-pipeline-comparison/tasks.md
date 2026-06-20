# Tasks — react-pipeline-comparison

---

## ⚙️ Deployment Workflow (áp dụng cho mọi phase)

> **Môi trường:** Code được viết trên **Windows** (`D:\awesome-llm-apps\llm-thesis`).
> Server thật chạy trên **Mac Mini** với Docker. DB Postgres chỉ tồn tại trên Mac Mini.
> Không có local DB trên Windows — không cần chạy Docker trên Windows.

**Mỗi khi hoàn thành một nhóm task, deploy như sau:**

```bash
# Bước 1 — Windows: commit và push lên GitHub
git add -A
git commit -m "feat(react-pipeline): <mô tả phase>"
git push origin main

# Bước 2 — Mac Mini: pull code mới về
cd ~/path/to/llm-thesis
git pull origin main

# Bước 3 — Mac Mini: restart chỉ fashion-api (postgres KHÔNG bị đụng vào)
docker compose -f fashion_agent/docker-compose.yml restart fashion-api

# Bước 4 — Mac Mini: verify DDL đã apply
docker compose -f fashion_agent/docker-compose.yml logs fashion-api --tail=20
# Tìm dòng: "Memory tables initialized."
```

**Tại sao không cần rebuild image:**
- `./agent` và `./api` được bind-mount vào container → Python files thay đổi ngay lập tức
- `init_memory_tables()` chạy tự động khi FastAPI khởi động → DDL mới apply lên Postgres thật
- `fashion-postgres` container và `pgdata` volume không bị restart → **data không mất**

---

## Phase 1: Database Schema

- [ ] 1.1 Add `orchestration_mode TEXT NOT NULL DEFAULT 'direct' CHECK (orchestration_mode IN ('direct', 'react'))` column to `user_sessions` in `agent/memory.py:init_memory_tables()` — idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
- [ ] 1.2 Add `response_latency_ms FLOAT NOT NULL DEFAULT 0` column to `llm_token_usage` — idempotent `ALTER TABLE`
- [ ] 1.3 Add `llm_call_count INT NOT NULL DEFAULT 1` column to `llm_token_usage` — idempotent `ALTER TABLE`
- [ ] 1.4 Create `react_traces` table — `(id BIGSERIAL PK, session_id TEXT FK, query_text TEXT, iteration INT, tool_name TEXT, tool_args JSONB, result_count INT, duration_ms FLOAT, traced_at TIMESTAMPTZ)` with index on `(session_id, traced_at)`
- [ ] 1.5 Create `eval_queries` table — `(id SERIAL PK, query_text TEXT, relevant_ids JSONB, category TEXT, difficulty TEXT CHECK IN ('easy','medium','hard'), language TEXT CHECK IN ('en','vi'), created_at TIMESTAMPTZ)`
- [ ] 1.6 Create `eval_results` table — `(id BIGSERIAL PK, eval_query_id INT FK, orchestration_mode TEXT, returned_ids JSONB, hit_at_1 BOOL, hit_at_3 BOOL, hit_at_6 BOOL, reciprocal_rank FLOAT, ndcg_at_6 FLOAT, latency_ms FLOAT, llm_call_count INT, total_tokens INT, run_at TIMESTAMPTZ)` with index on `(eval_query_id, orchestration_mode)`
- [ ] 1.7 Add `get_session_orchestration_mode(session_id: str) -> str` helper to `agent/memory.py` — `SELECT orchestration_mode FROM user_sessions WHERE session_id = %s`, returns `'direct'` as fallback
- [ ] 1.8 Update `create_session()` in `agent/memory.py` — add `orchestration_mode: str = 'direct'` parameter and persist it to `user_sessions`
- [ ] 1.9 Restart `fashion-api` container and verify DDL applies cleanly — check `docker compose logs fashion-api` for `"Memory tables initialized."`

## Phase 2: ReAct Agent Module

- [ ] 2.1 Create `agent/react_agent.py` — module docstring explaining: ReAct baseline pipeline, independent from `fashion_agent.py`, no shared in-memory state
- [ ] 2.2 Implement `_react_gate(classified: ClassifiedIntent) -> bool` — returns `False` if `intent in ("out_of_scope", "unclear")` or `confidence < REACT_CONFIDENCE_THRESHOLD` (default 0.50, env-overridable)
- [ ] 2.3 Implement `_log_react_traces(session_id, query_text, result: AgenticOrchestrationResult)` — iterates `result.tool_calls`, inserts one row per tool call into `react_traces` with iteration index, tool_name, tool_args, result_count, duration_ms
- [ ] 2.4 Implement `chat(message, session_id, ...) -> AgentResponse` in `react_agent.py`:
  - Fetch history, call `classify_intent()`
  - Call `_react_gate()` → if False, synthesize without search
  - If True, call `orchestrate_with_gemini(refined_query, history_text, ...)`
  - Call `_log_react_traces()`
  - Build synthesis context from `result.products`
  - Call `get_client().generate()` with `SYNTHESIS_PROMPT`
  - Call `add_message()`, `log_token_usage()` (with `response_latency_ms`, `llm_call_count`)
  - Return `AgentResponse`
- [ ] 2.5 Implement `chat_stream(message, session_id, ...) -> Generator` in `react_agent.py`:
  - Same flow as `chat()` but synthesis uses `get_client().stream()`
  - Yields `ThinkingEvent` steps (same event types as Direct: `"start"`, `"classify_done"`, `"search_done"`, `"done"`)
  - ReAct loop runs synchronously before streaming synthesis starts
- [ ] 2.6 Add `REACT_CONFIDENCE_THRESHOLD = float(os.getenv("REACT_CONFIDENCE_THRESHOLD", "0.50"))` module-level constant

## Phase 3: API Routing

- [ ] 3.1 Add `orchestration_mode: str = "direct"` field to `CreateSessionRequest` in `api/main.py` — validate `orchestration_mode in ("direct", "react")`, raise `ValueError` otherwise
- [ ] 3.2 Pass `orchestration_mode` from `CreateSessionRequest` to `create_session()` in the `POST /api/sessions` handler
- [ ] 3.3 Import `react_agent` in `api/main.py` alongside the existing `fashion_agent` import
- [ ] 3.4 In `POST /api/chat/stream` handler — add one DB call: `mode = get_session_orchestration_mode(session_id)` at the top of the handler
- [ ] 3.5 Branch dispatch: `if mode == "react": use agent_chat_stream from react_agent` else `use agent_chat_stream from fashion_agent` — both have identical signatures, no other changes needed
- [ ] 3.6 Apply same dispatch logic to `POST /api/chat` (non-streaming) handler

## Phase 4: Flutter Frontend

- [ ] 4.1 Add `orchestrationMode` parameter to `createSession()` in `clothie_web/lib/services/api_service.dart` — include `'orchestration_mode': orchestrationMode` in the POST body JSON
- [ ] 4.2 Add `String? _selectedMode` state variable to `_RegisterScreenState` in `register_screen.dart`
- [ ] 4.3 Add pipeline selector row to `_buildCard()` — two `_SelectButton` widgets in a `Row`: `⚡ Direct` (value `'direct'`) and `🔄 ReAct` (value `'react'`) — same layout and style as the gender selector row
- [ ] 4.4 Add validation in `_startChat()` — if `_selectedMode == null`, set `_error = 'Please select your preferred agent mode.'`
- [ ] 4.5 Pass `_selectedMode!` as `orchestrationMode` argument to `_api.createSession()` in `_startChat()`

## Phase 5: Ground Truth Dataset

- [ ] 5.1 Create `evaluation/eval_queries.json` — 40 queries following the schema: `[{query_text, relevant_ids[], category, difficulty, language}]`
  - 10 EN Easy: single-category + 1 attribute (e.g., `"white slim fit shirt for men"`)
  - 8 EN Medium: 2–3 attributes (e.g., `"casual floral summer dress pastel color"`)
  - 8 EN Hard: outfit/occasion level (e.g., `"smart casual office look for women"`)
  - 4 VI Easy: (e.g., `"áo hoodie màu đen oversize nam"`)
  - 4 VI Medium: (e.g., `"váy hoa nhí pastel dáng xòe"`)
  - 6 VI Hard: (e.g., `"trang phục đi làm lịch sự nữ"`)
  - Each query: 1–3 `relevant_ids` verified against Qdrant collection
- [ ] 5.2 Create `evaluation/seed_eval_queries.py` — reads `eval_queries.json`, connects to Postgres, inserts rows into `eval_queries` (idempotent: skip if `query_text` already exists)
- [ ] 5.3 Run `seed_eval_queries.py` on the Mac Mini server (or via SSH + DB tunnel) to populate the `eval_queries` table

## Phase 6: Offline Evaluation Runner

- [ ] 6.0 Create `test_tool.py` as a short pilot harness (5–10 queries) that runs both pipelines with fresh sessions, prints returned IDs / latency / tokens, and exits loudly on any failure
- [ ] 6.1 Create `evaluation/run_comparison.py` — CLI script:
  - Loads all rows from `eval_queries`
  - For each query, runs Direct pipeline: `fashion_agent.chat(query_text, fresh_session_id)`; records `returned_ids`, `latency_ms`, `total_tokens`, `llm_call_count`
  - For each query, runs ReAct pipeline: `react_agent.chat(query_text, fresh_session_id)`; records same fields
  - Computes per-query: `hit_at_1`, `hit_at_3`, `hit_at_6`, `reciprocal_rank` (for MRR), `ndcg_at_6`
  - Inserts results into `eval_results`
  - Prints a summary table to stdout (mode | Hit@1 | Hit@3 | Hit@6 | MRR | NDCG@6 | Avg Latency | Avg Tokens)
- [ ] 6.2 Add `--runs N` flag (default 1) to repeat the evaluation N times — enables mean ± std reporting
- [ ] 6.3 Add `--mode [direct|react|both]` flag (default `both`) for partial re-runs
- [ ] 6.4 Run `run_comparison.py --runs 3` on Mac Mini and verify `eval_results` is populated
- [ ] 6.5 Run `test_tool.py` first on a pilot subset, then only proceed to the full 40-query benchmark if the smoke test is clean

## Phase 7: Notebook Extension

- [ ] 7.1 Add Section 7 `## 7 · Direct vs ReAct — Offline Evaluation` to `analysis/thesis_evaluation.ipynb`:
  - Pull from `eval_results` grouped by `orchestration_mode`
  - Compute mean ± std for Hit@1, Hit@3, Hit@6, MRR, NDCG@6
  - Bar chart: Hit@K comparison side by side
  - Line chart: MRR by difficulty tier (Easy / Medium / Hard)
- [ ] 7.2 Add Section 8 `## 8 · Direct vs ReAct — Efficiency Metrics`:
  - Pull `avg(latency_ms)`, `avg(llm_call_count)`, `avg(total_tokens)` from `eval_results` by mode
  - Bar chart: latency comparison
  - Bar chart: token cost comparison
  - Compute cost ratio: `avg_tokens_react / avg_tokens_direct`
- [ ] 7.3 Add Section 9 `## 9 · ReAct Trace Analysis`:
  - Pull `react_traces` — avg iterations per query, tool call distribution (search vs. recommend), correlation between iterations and Hit@6
- [ ] 7.4 Add Section 10 `## 10 · Online Behavioural Comparison (Direct vs ReAct)`:
  - Reuse existing SR/SCR/QRR/Conversion logic from Section 2 but filter `orchestration_mode IN ('direct', 'react')`
  - Report per-mode behavioural metrics from live sessions

## Phase 8: Testing & Verification

- [ ] 8.1 Write `tests/test_react_agent.py` — unit tests:
  - `test_gate_blocks_out_of_scope()` — `_react_gate()` returns False for `intent="out_of_scope"`
  - `test_gate_blocks_low_confidence()` — returns False when `confidence < 0.50`
  - `test_gate_passes_valid_intent()` — returns True for `intent="text_search"`, `confidence=0.85`
  - `test_chat_returns_agent_response()` — mock `orchestrate_with_gemini`, assert `AgentResponse` returned
  - `test_react_traces_logged()` — mock DB, assert `_log_react_traces()` inserts correct row count
- [ ] 8.2 Write `tests/test_react_routing.py` — API routing tests:
  - `test_direct_session_routes_to_fashion_agent()` — mock both agents, assert correct one called
  - `test_react_session_routes_to_react_agent()` — same
  - `test_unknown_mode_defaults_to_direct()` — assert fallback behaviour
- [ ] 8.3 Verify `tests/test_orchestration_modes.py` still passes (no regression in Mode A)
- [ ] 8.4 Manual smoke test on Mac Mini:
  - Register a `react` session via Flutter UI
  - Send a fashion search query
  - Verify `react_traces` has rows in Postgres: `SELECT * FROM react_traces LIMIT 5;`
  - Verify `llm_token_usage.orchestration_mode = 'react'` for the session
- [ ] 8.5 Manual smoke test — `direct` session:
  - Register a `direct` session, send same query
  - Verify `fashion_agent.py` slot cache is populated (check `_session_accumulated_slots`)
  - Verify `react_traces` has NO rows for this session
- [ ] 8.6 Run `evaluation/run_comparison.py --runs 1` and confirm `eval_results` table has 80 rows (40 queries × 2 modes)

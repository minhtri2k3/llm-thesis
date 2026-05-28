## Context

The Fashion Agent v2 uses a Direct pipeline (`fashion_agent.py`) with deterministic routing: intent classify → slot gate → hybrid search → synthesis. This pipeline was deliberately built to replace an earlier ReAct loop that had reliability and latency issues. The thesis currently reports Hit@6 from this pipeline only, which is insufficient for peer review — a baseline comparison is required to demonstrate the contribution of the specialized design.

The `agentic_orchestrator.py` module already contains a working `orchestrate_with_gemini()` function (native Gemini tool-calling loop, max 4 iterations) that was built as infrastructure for Mode B but never wired to user-facing sessions. This is the natural substrate for the ReAct baseline.

The system already tracks `orchestration_mode` in `llm_token_usage`, has a `mode_cost_summary` DB view, and the analysis notebook already segments by mode. The missing piece is: (1) a complete ReAct session path, (2) the pipeline selector at registration, (3) offline evaluation infrastructure.

## Goals / Non-Goals

**Goals:**
- Implement a ReAct baseline pipeline that is fully independent from the Direct pipeline
- Tag every session, event, and metric row with `orchestration_mode` from registration time
- Provide offline evaluation infrastructure (ground truth queries + runner script) for Hit@K, MRR, NDCG, latency comparison
- Log ReAct iteration traces for overhead analysis (avg iterations, tool diversity)
- Extend the thesis notebook with a Direct vs ReAct comparison section
- Keep the change safe to deploy on the live Mac Mini server: only `fashion-api` restart required, no data loss

**Non-Goals:**
- Modifying `fashion_agent.py` (Direct pipeline must remain untouched)
- Streaming the ReAct loop (synthesis streaming is sufficient; loop runs synchronously)
- Adding tools beyond `search_fashion` and `recommend_outfit` to the ReAct agent
- Real-time side-by-side mode comparison in the UI
- Automated ground truth generation (manual annotation for 40 queries)

## Decisions

### D1: Separate module, not a branch inside `fashion_agent.py`

**Decision:** Implement the ReAct pipeline as `agent/react_agent.py` with its own `chat()` and `chat_stream()` functions. The routing decision lives exclusively in `api/main.py`.

**Why:** `fashion_agent.py` carries four TTL-cached dictionaries keyed by `session_id` (`_session_accumulated_slots`, `_session_ranked_slots`, `_session_last_results`, `_session_pending_selection`). These implement slot accumulation and selection-flow logic that is intrinsic to the Direct pipeline's multi-turn design. If a ReAct session shared these caches — even passively — stale slot state from a previous Direct session could corrupt ReAct's classification gate, or ReAct's results could contaminate the Direct pipeline's `_session_last_results`. Complete module isolation eliminates this class of bug entirely and makes each pipeline independently testable and removable.

**Alternative considered:** A flag parameter inside `fashion_agent.chat_stream()` — rejected because it would add branches throughout the 400-line function and make the slot cache exposure implicit.

---

### D2: Intent classification as the ReAct gate

**Decision:** `react_agent.py` calls `classify_intent()` before entering the Gemini tool-calling loop. If `intent in ("out_of_scope", "unclear")` or `confidence < 0.50`, the loop is skipped and the query is synthesized directly with no tool calls.

**Why:** Without a gate, the Gemini orchestrator would attempt tool calls on greetings, off-topic queries, and ambiguous inputs — wasting tokens and producing poor results. The gate mirrors the Direct pipeline's intent check, making the comparison fair: both pipelines handle non-search intents without search, and both enter search for valid intents. The threshold `0.50` is intentionally lower than the Direct pipeline's `SEARCH_CONFIDENCE_THRESHOLD` (default `0.75`) so the ReAct loop has a broader entry condition, reflecting its agentic nature.

**Confidence threshold:** `REACT_CONFIDENCE_THRESHOLD = 0.50` (env-overridable, default 0.50).

---

### D3: `orchestrate_with_gemini()` reused as-is

**Decision:** `react_agent.py` imports and calls `orchestrate_with_gemini()` from `agentic_orchestrator.py` without modification.

**Why:** The function is already production-quality (error handling, token counting, 4-iteration hard cap, structured `AgenticOrchestrationResult`). Reusing it avoids duplication and keeps the ReAct tool-call behaviour identical to what was already designed and tested for Mode B. Any improvements to the orchestrator benefit both.

---

### D4: `orchestration_mode` written at session creation, read at every request

**Decision:** `user_sessions.orchestration_mode` is set once during `POST /api/sessions` and read by `api/main.py` at the start of every `POST /api/chat/stream` request via a new `get_session_orchestration_mode(session_id)` helper in `memory.py`.

**Why:** Writing mode once at registration ensures the entire session — including all behavioural events (impressions, clicks, selections) — is consistently attributed to one pipeline. Reading from the DB per request (rather than caching in memory) keeps the routing stateless and safe for multi-replica deployments, and costs only one lightweight `SELECT` per message.

**Alternative considered:** Passing `orchestration_mode` as a field in every `ChatRequest` — rejected because it would require the Flutter client to remember and re-send the mode on every message, creating a risk of mode drift mid-session.

```python
# New helper in memory.py
def get_session_orchestration_mode(session_id: str) -> str:
    """Return 'direct' | 'react'. Defaults to 'direct' if session not found."""
```

---

### D5: `react_traces` table for per-iteration logging

**Decision:** Each tool-call iteration made by `orchestrate_with_gemini()` during a ReAct session is persisted to a new `react_traces` table with columns: `session_id`, `query_text`, `iteration` (0-indexed), `tool_name`, `tool_args` (JSONB), `result_count`, `duration_ms`, `traced_at`.

**Why:** `react_traces` enables three thesis analyses that are not otherwise measurable: (a) average number of iterations per query, (b) which tool is called most (search vs. recommend), (c) whether multi-iteration queries produce better behavioural outcomes than single-iteration ones. This is the key "interpretability" advantage of the ReAct pipeline from a thesis perspective.

**Alternative considered:** Storing traces inside `llm_token_usage.tool_calls_json` (already exists) — rejected because `tool_calls_json` is per-turn (session level) and does not capture the per-query iteration breakdown needed for analysis.

---

### D6: Offline evaluation — fixed query set, script runner, DB results

**Decision:** 40 manually annotated queries are stored in `evaluation/eval_queries.json` and seeded into the `eval_queries` Postgres table. A script `evaluation/run_comparison.py` iterates over all queries, calls both pipelines in sequence, measures latency, and inserts results into `eval_results`.

**Why:** Offline evaluation with a fixed ground truth set is the only way to compare Hit@K, MRR, and NDCG between the two pipelines in a controlled, reproducible way. Online behavioural data (clicks, selections) provides complementary evidence but cannot give ground truth relevance. The 40-query set covers three difficulty tiers and two languages to test generalization. Results in `eval_results` are queryable from the thesis notebook directly.

**Query set composition:**

| Tier | Count | Description | Example |
|------|-------|-------------|---------|
| Easy | 10 EN + 4 VI | Single category + 1 attribute | `"white slim fit shirt for men"` |
| Medium | 8 EN + 4 VI | Multi-attribute (2–3 filters) | `"casual floral summer dress pastel"` |
| Hard | 8 EN + 6 VI | Outfit-level / occasion-based | `"business casual interview outfit women"` |

Each query has 1–3 `relevant_ids` (manually verified `image_id` values from the Qdrant collection).

---

### D7: No DB rebuild, no container rebuild for schema changes

**Decision:** All new DDL is added as idempotent statements (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`) inside `init_memory_tables()` in `memory.py`. Schema migration is applied automatically on `docker compose restart fashion-api` (~30 seconds).

**Why:** The `./agent` directory is bind-mounted into the `fashion-api` container, so Python file changes are visible immediately without rebuilding the image. `init_memory_tables()` runs on every FastAPI startup (lifespan hook). Adding `NOT NULL DEFAULT 'direct'` to `user_sessions` backfills existing rows with the default — PostgreSQL handles this atomically with no data loss. The `fashion-postgres` container and `pgdata` volume are never restarted.

---

### D8: Flutter pipeline selector — same visual component as gender selector

**Decision:** The pipeline selector in `register_screen.dart` uses the existing `_SelectButton` widget with two options: `⚡ Direct` and `🔄 ReAct`. It follows the same row layout as the gender selector. The selection is required (validation mirrors gender: must choose before proceeding).

**Why:** Reusing `_SelectButton` ensures visual consistency with zero new widget code. Making selection required prevents ambiguous sessions where `orchestration_mode` is unknown. Placing the selector below gender and above the model display label follows the natural information hierarchy of the registration form.

```
[  Boy 👦  ]  [  Girl 👧  ]   ← existing gender row
[⚡ Direct  ]  [🔄 ReAct  ]   ← new pipeline row (same style)
Model: Gemini 2.5 Flash        ← existing display
```

## Risks / Trade-offs

- **ReAct latency makes live comparison subjective** — Users who chose ReAct will experience 3–5× slower responses. Mitigated by clearly labelling the pipeline in the UI so users know what to expect, and by measuring latency quantitatively in `eval_results`.

- **Small behavioral sample per mode** — With real users split across two modes, each mode may have insufficient sessions for statistical significance. Mitigation: offline `eval_results` provides the primary statistical comparison; online behavioral data is secondary evidence. Report bootstrap CIs for all online metrics.

- **Annotation bias in ground truth** — Manual annotation of `eval_queries` by a single annotator (the thesis author) introduces bias. Mitigation: document annotation guidelines in `evaluation/eval_queries.json` schema; use well-defined relevance criterion (product appears in top result from a neutral keyword search of the Qdrant collection).

- **`orchestrate_with_gemini()` non-determinism** — Gemini tool-calling is non-deterministic; the same query may produce different tool sequences across runs. Mitigation: run `evaluation/run_comparison.py` 3× and report mean ± std for each metric. Store all runs in `eval_results` (identified by `run_at`).

- **`react_agent.py` has no slot accumulation** — Multi-turn refinement ("show me something bluer") works differently in ReAct vs Direct. The ReAct agent may not carry slot context across turns. Mitigation: this is a documented design difference, not a bug. The thesis should explicitly discuss this as a trade-off: Direct has engineered slot memory; ReAct relies on the LLM's in-context history.

## Migration Plan

1. Add DDL to `memory.py` — run on `docker compose restart fashion-api` (no data loss)
2. Create `agent/react_agent.py` — bind-mounted, visible immediately after container restart
3. Update `api/main.py` — routing dispatch, new `CreateSessionRequest` field
4. Update Flutter — `api_service.dart` + `register_screen.dart`
5. Seed ground truth — run `evaluation/seed_eval_queries.py` once after DB migration
6. Run offline eval — `evaluation/run_comparison.py` (can run on Mac Mini or local with DB tunnel)
7. Extend notebook — Section 7 added to `analysis/thesis_evaluation.ipynb`

## Open Questions

- What is the minimum `relevant_ids` count acceptable per query? (Proposed: at least 1, prefer 2–3)
- Should the Flutter UI display the pipeline mode in the chat screen header? (Proposed: no — keep it clean; mode is visible at registration only)
- Should `react_traces` be included in the Professor Dashboard analytics? (Proposed: yes — add avg iterations per mode to the existing token analytics view)

## 1. Configuration & feature flag

- [x] 1.1 Add `ENABLE_COHORT_STUDY: ${ENABLE_COHORT_STUDY:-false}` to `docker-compose.yml` next to `ENABLE_PATH2_IMAGE_SEARCH`
- [x] 1.2 Document `ENABLE_COHORT_STUDY` in `.env` example with default `false`
- [x] 1.3 Add `_is_cohort_study_enabled()` helper in `api/main.py` mirroring `_is_path2_enabled()` (`api/main.py:192`)
- [x] 1.4 Verify `GEMINI_API_KEY` already in `.env`; no new keys needed

## 2. Codename mapping module

- [x] 2.1 Create `fashion_agent/agent/cohort.py` exposing `CODENAME_TO_MODEL: dict[str, str]`, `MODEL_TO_CODENAME: dict[str, str]`, `COHORT_MODELS: list[str]`, and `LATIN_SQUARE: list[list[str]]` (4x4 array of codenames per group)
- [x] 2.2 Constants:
  - `Indigo`  → `gemini-2.5-flash`
  - `Crimson` → `gemini-2.5-pro`
  - `Emerald` → `gemini-3.1-flash-lite`
  - `Amber`   → `gemini-3.1-pro-preview`
- [x] 2.3 Add `assign_codename_for_session(group: str, session_index: int) -> str` reading the Latin square
- [x] 2.4 Unit tests: every model appears once per session-position; group resolution is deterministic; session_index ≥ 4 raises `ValueError`

## 3. Database schema (additive only)

- [x] 3.1 In `agent/memory.py:init_memory_tables()`, add `ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS study_group TEXT` and `ADD COLUMN IF NOT EXISTS agent_codename TEXT`
- [x] 3.2 Add `ALTER TABLE llm_token_usage ADD COLUMN IF NOT EXISTS latency_ms INT NOT NULL DEFAULT 0`, same for `intent_latency_ms` and `synthesis_latency_ms`
- [x] 3.3 Verify the existing `session_token_summary` view still compiles (it should; it only `MAX/SUM`s columns it already references)
- [ ] 3.4 Manual smoke: start container, drop into psql, `\d user_sessions` and `\d llm_token_usage` should show new columns

## 4. Backend — validator + assignment

- [x] 4.1 Widen `CreateSessionRequest` validator in `api/main.py` (around `:108-127`) to accept any of the 4 cohort model IDs IF `ENABLE_COHORT_STUDY=true`; otherwise behaviour unchanged
- [x] 4.2 Add `assign_cohort_session(user_name: str) -> tuple[group, codename, model_id, session_index]` in `agent/memory.py`:
  - On 1st session for a user_name: round-robin assign group from `(SELECT COUNT(DISTINCT user_name)) % 4`
  - On 2nd-4th: increment `session_index` for that user
  - On 5th+: raise `CohortStudyExhausted` (caught in API, returned as HTTP 409)
- [x] 4.3 Modify `create_session_endpoint` to call `assign_cohort_session()` when flag is on; override request's `preferred_model` with assigned model; persist `study_group`, `agent_codename`
- [x] 4.4 When flag is off, `create_session()` behaves exactly as today (no schema interaction with new columns)

## 5. Backend — startup smoke test

- [x] 5.1 In FastAPI lifespan handler, when `ENABLE_COHORT_STUDY=true` call `_smoke_test_cohort_models()` which iterates `COHORT_MODELS` and pings each via `GeminiClient(m).generate("ping")`
- [x] 5.2 Failed cells append to module-level `_UNREACHABLE_CODENAMES`; `assign_cohort_session()` consults this set and skips unreachable codenames
- [x] 5.3 Loud `logger.error(...)` per failed model; if all 4 fail, lifespan still starts (so non-cohort traffic isn't broken) but log fatal warning
- [x] 5.4 Test: monkeypatch `GeminiClient.generate` to raise on `gemini-3.1-pro-preview`; verify that codename is skipped from rotation

## 6. Backend — latency instrumentation

- [x] 6.1 In `agent/fashion_agent.py`, wrap `classify_intent(...)` call (currently `:809`) with `time.perf_counter()`; capture `intent_latency_ms`
- [x] 6.2 Wrap synthesis stream consumption (currently `:1543-1550`) with `time.perf_counter()`; capture `synthesis_latency_ms`
- [x] 6.3 Capture total turn latency from `_orchestrate_stream()` entry to final `done` SSE
- [x] 6.4 Extend `log_token_usage()` signature in `agent/memory.py:796` with three new optional kwargs: `latency_ms: int = 0`, `intent_latency_ms: int = 0`, `synthesis_latency_ms: int = 0`; insert into the new columns
- [x] 6.5 Update both `log_token_usage()` callsites in `fashion_agent.py` (`:842` intent, `:1571` synthesis) to pass the relevant latencies
- [ ] 6.6 Manual smoke: trigger a chat, query `SELECT call_name, latency_ms, intent_latency_ms, synthesis_latency_ms FROM llm_token_usage ORDER BY created_at DESC LIMIT 4;`

## 7. Backend — cohort analytics endpoint

- [x] 7.1 Add `cohort_summary()` in `api/analytics.py` joining `llm_token_usage` × `user_sessions` × `user_ratings` × `session_path_funnel_summary`, grouped by `agent_codename`, filtered `study_group IS NOT NULL`
- [x] 7.2 Aggregate per cell: n_sessions, n_turns, avg input/output tokens per turn, p50/p95 latency (total + intent + synthesis), click-through rate, cart adds per session, avg rating, clarification rate, turns-to-first-cart
- [x] 7.3 Add `GET /api/analytics/cohort` route in `api/main.py` (admin-protected, mirror `/api/analytics/token-usage`)
- [x] 7.4 Response includes `mapping` (codename → model) read from `agent/cohort.py`
- [x] 7.5 If `ENABLE_COHORT_STUDY=false`, endpoint returns 503 with `{"detail": "cohort study not enabled"}`
- [ ] 7.6 Test with seeded fixtures: 4 testers × 4 sessions; verify each cell has counts > 0 and SQL terminates without error

## 8. Frontend — Flutter changes

- [x] 8.1 In `clothie_web/lib/screens/register_screen.dart`, when cohort mode is on, replace the model field with read-only label "You are testing: {{codename}}"
- [x] 8.2 The `/api/sessions` response already returns the assigned codename — display it on the chat screen header so the tester sees which agent they're using right now
- [x] 8.3 In `clothie_web/lib/screens/professor_dashboard_page.dart`, add a "Cohort Study" tab consuming `/api/analytics/cohort`
- [x] 8.4 Cohort tab renders a 4-column table (Indigo, Crimson, Emerald, Amber) with the rows: tokens (in/out/per session), latency p50/p95, click-through %, carts/session, avg rating, clarification %
- [x] 8.5 Header strip explicitly shows mapping: "Indigo = gemini-2.5-flash | Crimson = gemini-2.5-pro | Emerald = gemini-3.1-flash-lite | Amber = gemini-3.1-pro-preview"
- [x] 8.6 Add `getCohortAnalytics()` method in `clothie_web/lib/services/api_service.dart`

## 9. Tests

- [x] 9.1 Confirm `tests/test_orchestration_modes.py` (8 assertions) still passes unchanged
- [x] 9.2 New `tests/test_cohort_assignment.py`:
  - 16 sequential `assign_cohort_session("user{i}")` calls fill the 4×4 grid evenly
  - 5th session for the same user raises `CohortStudyExhausted`
  - Unreachable codename in `_UNREACHABLE_CODENAMES` is skipped
- [ ] 9.3 New `tests/test_cohort_analytics.py`: seed 4 sessions × 4 codenames, call `cohort_summary()`, assert mapping correctness and that pre-study (NULL `study_group`) rows are excluded
- [ ] 9.4 New `tests/test_latency_logging.py`: mock `time.perf_counter`, run `chat_stream()`, assert `latency_ms`, `intent_latency_ms`, `synthesis_latency_ms` are non-zero in the resulting `llm_token_usage` row
- [x] 9.5 Run full suite: `pytest tests/ -x` with flag off and on

## 10. Regression checklist (manual, before enabling on production)

- [ ] 10.1 With `ENABLE_COHORT_STUDY=false`: register, chat, confirm a selection, view leaderboard — identical to today
- [ ] 10.2 Inspect `\d user_sessions` and `\d llm_token_usage` post-migration; confirm new columns exist and existing rows have NULL/0 defaults
- [ ] 10.3 With `ENABLE_COHORT_STUDY=true`: register 4 testers, walk each through 4 sessions, verify each codename appears once in each session position across the cohort
- [ ] 10.4 Visit professor dashboard's Cohort tab; verify 4 cells populate; verify the codename↔model mapping is visible
- [ ] 10.5 Flip flag to `false`; new registrations revert to single-model; existing cohort data remains queryable via the dashboard endpoint (which now returns 503 — but data is intact)

## 11. Documentation

- [x] 11.1 Update `CLAUDE.md` with a one-paragraph note about `ENABLE_COHORT_STUDY` and where the codename map lives
- [ ] 11.2 Add a short README section in `fashion_agent/` describing how to run the study (set flag, recruit, walk through 4 sessions)
- [ ] 11.3 Note in `docs/handover.md` that schema columns are additive and the dashboard endpoint is admin-only

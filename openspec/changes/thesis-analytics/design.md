## Context

The Fashion Agent backend (`fashion_agent/`) is a Python FastAPI + Gradio application backed by PostgreSQL. The agent uses Gemini (`shared/llm.py`) for intent classification (`agent/intent_classifier.py`) and response synthesis (`agent/fashion_agent.py`). Token usage (`prompt_token_count`, `candidates_token_count`) is already extracted from `response.usage_metadata` in both callsites but only placed into in-memory SSE events — never written to the database.

The Flutter frontend (`clothie_web/`) communicates via REST. The Register screen already has a `_LeaderboardDialog` as a model for a secondary dialog widget. The `ApiService` handles all HTTP calls.

## Goals / Non-Goals

**Goals:**
- Persist per-call token counts (input + output) to a new `llm_token_usage` table after every intent classification and synthesis call
- Record the model name used for each call (hardcoded as `"gemini-2.5-flash"` for now; Change B will make this dynamic)
- Expose token analytics via a new protected endpoint `GET /api/analytics/token-usage` requiring `ADMIN_SECRET_KEY` header
- Render a "🔬 Professor View" button on the Register screen that presents an 8-digit PIN dialog then a dashboard showing Model Name, Total Tokens, Session ID, User Name per session

**Non-Goals:**
- Multi-model provider abstraction (Change B)
- Reranker `selection_rank` tracking (deferred — additive later)
- Token cost estimation in dollars
- Real-time token streaming to the dashboard

## Decisions

### D1 — Store tokens in a dedicated table, not in `user_sessions`
`user_sessions` models one row per session; token usage is multi-row (one per LLM call). A separate `llm_token_usage` table with a FK to `session_id` is the correct schema. A `session_token_summary` VIEW aggregates for reporting without denormalizing the base table.

**Alternative considered**: Add `intent_input_tokens`, `intent_output_tokens`, `synthesis_input_tokens`, `synthesis_output_tokens` columns to `user_sessions`. Rejected because it precludes recording clarification calls or future call types without further migrations.

### D2 — Log tokens after each call returns, not asynchronously
Both `classify_intent()` and `_synthesize_response_stream()` already execute synchronously or block until the stream is exhausted. Inserting to the DB synchronously (same transaction context) is safe and simplest. No background task queue needed.

**Alternative considered**: Use `asyncio.create_task()` to fire-and-forget DB write. Rejected because it adds complexity and risks losing data on process crash.

### D3 — Use `X-Admin-Key` request header for dashboard auth (not a Bearer token)
This is a single-tenant thesis tool — there is no user authentication system. A shared secret in an HTTP header is appropriate and matches the professor's usage pattern (API client or Flutter UI sends the key once per request).

**Alternative considered**: Query param `?secret_key=`. Rejected because it appears in server access logs.

### D4 — Database migration via Python `init_db()` call at startup (additive DDL)
`memory.py` already calls `CREATE TABLE IF NOT EXISTS` at startup. Append the new `llm_token_usage` DDL to the same `init_db()` function. The `IF NOT EXISTS` guard makes it safe to re-run on every deploy.

**Alternative considered**: Separate Alembic migration. Rejected as over-engineering for a thesis project with no prod/staging split.

### D5 — Flutter PIN dialog as a simple `TextFormField` with `obscureText: true`
The existing `_LeaderboardDialog` widget pattern (in `register_screen.dart`) is the exact pattern to copy. The PIN dialog → sends HTTP POST  → on 200 loads dashboard; on 403 shows error. No token caching on the Flutter side.

## Risks / Trade-offs

- **Secret visible in Flutter binary** → The `ADMIN_SECRET_KEY` is sent over HTTPS; someone decompiling the APK could observe it only if they intercept a real request. For a thesis demo this is acceptable; for production a proper auth system would be needed.
- **`init_db()` runs on every process start** → `IF NOT EXISTS` makes it idempotent; no risk of data loss on restart.
- **Token counts at 0 if Gemini rate-limits and returns no usage metadata** → Defensive `getattr(..., 0) or 0` pattern already used in both callsites; 0 will be logged rather than crashing.
- **Concurrent requests write to `llm_token_usage` simultaneously** → PostgreSQL handles row-level locks; BIGSERIAL PK ensures no collision.

## Migration Plan

1. Deploy updated `agent/memory.py` → `init_db()` creates `llm_token_usage` table and `session_token_summary` view on first startup
2. Add `ADMIN_SECRET_KEY=21042024` to `.env`
3. Restart `fashion_agent` container
4. Rebuild Flutter web (`flutter build web`) and redeploy `clothie_web`

**Rollback**: Remove `log_token_usage()` calls from `fashion_agent.py`; the table remains but no new rows are written. Data already logged is preserved.

## Open Questions

- None — all decisions are made. Change B (multi-model provider) will revisit D1 to add `provider` and `is_estimated` columns.

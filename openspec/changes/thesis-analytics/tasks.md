## 1. Environment & Configuration

- [x] 1.1 Add `ADMIN_SECRET_KEY=21042024` to `fashion_agent/.env`
- [x] 1.2 Add `ADMIN_SECRET_KEY=your_admin_secret_here` to `fashion_agent/.env.example` with a comment

## 2. Database — Token Tracking Table & View

- [x] 2.1 In `fashion_agent/agent/memory.py` `init_db()`, add `CREATE TABLE IF NOT EXISTS llm_token_usage` DDL with columns: `id BIGSERIAL PRIMARY KEY`, `session_id TEXT REFERENCES user_sessions(session_id) ON DELETE CASCADE`, `call_name TEXT NOT NULL`, `model_name TEXT NOT NULL`, `input_tokens INT NOT NULL DEFAULT 0`, `output_tokens INT NOT NULL DEFAULT 0`, `created_at TIMESTAMPTZ DEFAULT NOW()`
- [x] 2.2 In `init_db()`, add `CREATE OR REPLACE VIEW session_token_summary AS SELECT s.session_id, s.user_name, MAX(u.model_name) AS model_name, SUM(u.input_tokens) AS total_input_tokens, SUM(u.output_tokens) AS total_output_tokens, SUM(u.input_tokens + u.output_tokens) AS total_tokens, s.created_at::date AS session_date FROM llm_token_usage u JOIN user_sessions s USING (session_id) GROUP BY s.session_id, s.user_name, s.created_at`
- [x] 2.3 Add `log_token_usage(conn_or_pool, session_id: str, call_name: str, model_name: str, input_tokens: int, output_tokens: int)` function in `memory.py` that inserts one row into `llm_token_usage`
- [x] 2.4 Add `get_token_analytics(conn_or_pool)` function in `memory.py` that runs `SELECT * FROM session_token_summary ORDER BY session_date DESC, total_tokens DESC` and returns a list of dicts

## 3. Backend — Token Logging Hooks

- [x] 3.1 In `fashion_agent/agent/fashion_agent.py`, after `classify_intent()` returns, call `log_token_usage(session_id=session_id, call_name="intent", model_name="gemini-2.5-flash", input_tokens=intent.input_tokens, output_tokens=intent.output_tokens)` — wrap in try/except so a DB error never kills the chat stream
- [x] 3.2 In `_synthesize_response_stream()`, in the block where `TokenUsage` is yielded (after the stream exhausts), call `log_token_usage(session_id=session_id, call_name="synthesis", model_name="gemini-2.5-flash", input_tokens=in_tok, output_tokens=out_tok)` — same try/except guard

## 4. Backend — Analytics API Endpoint

- [x] 4.1 In `fashion_agent/api/main.py`, add `GET /api/analytics/token-usage` endpoint that reads `X-Admin-Key` header, compares to `os.getenv("ADMIN_SECRET_KEY")`, returns 503 if env var not set, returns 403 if key mismatch, otherwise calls `get_token_analytics()` and returns `{"sessions": [...], "total_sessions": N, "grand_total_tokens": M}`

## 5. Flutter — API Service

- [x] 5.1 In `clothie_web/lib/services/api_service.dart`, add `getTokenAnalytics(String secretKey)` async method that calls `GET $kApiBaseUrl/api/analytics/token-usage` with header `X-Admin-Key: $secretKey`, returns `List<Map<String, dynamic>>` from the `sessions` field, throws on non-200

## 6. Flutter — Professor Dashboard UI

- [x] 6.1 In `clothie_web/lib/screens/register_screen.dart`, add a "🔬 Professor View" `GestureDetector` button below the existing Leaderboard button, styled identically (same `kSurfaceColor`, `kAccentLight`, border, padding)
- [x] 6.2 Add `_showProfessorPin()` method that calls `showDialog` with a new `_PinDialog` widget; on successful PIN validation (`_PinDialog` returns the validated secret key), immediately call `_showProfessorDashboard(secretKey)`
- [x] 6.3 Implement `_PinDialog` stateful widget: obscured `TextField` (8-char max, numeric keyboard), "Cancel" and "Unlock 🔬" buttons; on submit calls `widget.api.getTokenAnalytics(pin)` — on 200 pops and returns the pin, on 403 sets local `_error = "Incorrect access code"` state, validates non-empty before any HTTP call
- [x] 6.4 Add `_showProfessorDashboard(String secretKey)` method that calls `showDialog` with a new `_ProfessorDashboardDialog` widget
- [x] 6.5 Implement `_ProfessorDashboardDialog` stateful widget: loads data in `initState()` via `widget.api.getTokenAnalytics(secretKey)`, shows `CircularProgressIndicator` while loading, renders a `ListView` with one row per session displaying Session ID (first 12 chars + "…"), User Name, Model Name, Total Tokens formatted with comma separator; shows empty state text if list is empty; shows error text if request fails; has header "🔬 Professor Dashboard" with close button and a summary line "N sessions · M total tokens"

## ADDED Requirements

### Requirement: Token usage persisted after every LLM call
The system SHALL write one row to `llm_token_usage` for every call to `classify_intent()` and every completed `_synthesize_response_stream()` invocation. Each row SHALL contain: `session_id`, `call_name` (`"intent"` or `"synthesis"`), `model_name` (the Gemini model string), `input_tokens`, `output_tokens`, and `created_at`.

#### Scenario: Intent classification tokens logged
- **WHEN** `classify_intent()` returns a `ClassifiedIntent` result
- **THEN** a row is inserted into `llm_token_usage` with `call_name="intent"`, `input_tokens=ClassifiedIntent.input_tokens`, `output_tokens=ClassifiedIntent.output_tokens`, and `model_name="gemini-2.5-flash"`

#### Scenario: Synthesis tokens logged
- **WHEN** `_synthesize_response_stream()` yields its final `TokenUsage` event
- **THEN** a row is inserted into `llm_token_usage` with `call_name="synthesis"`, `input_tokens` and `output_tokens` from the `TokenUsage` event, and `model_name="gemini-2.5-flash"`

#### Scenario: Zero tokens on Gemini metadata absence
- **WHEN** `response.usage_metadata` is absent or returns 0 for token counts
- **THEN** the system still inserts a row with `input_tokens=0` and `output_tokens=0` rather than raising an exception

### Requirement: Session token summary view provides aggregate data
The system SHALL maintain a `session_token_summary` PostgreSQL VIEW that aggregates `llm_token_usage` rows by `session_id`, joining to `user_sessions` for the `user_name`, summing `input_tokens` and `output_tokens`, and exposing `total_tokens = input_tokens + output_tokens`.

#### Scenario: Summary includes sessions with no tokens yet
- **WHEN** a session exists in `user_sessions` but has no rows in `llm_token_usage`
- **THEN** that session does NOT appear in `session_token_summary` (inner join semantics acceptable for thesis reporting)

#### Scenario: Summary reflects all calls per session
- **WHEN** a session has 3 LLM calls (1 intent + 1 synthesis + 1 clarification)
- **THEN** `session_token_summary.total_tokens` equals the sum of all 3 rows

### Requirement: `init_db()` creates `llm_token_usage` table idempotently
The system SHALL use `CREATE TABLE IF NOT EXISTS` DDL for `llm_token_usage` so that restarting the process does not cause errors and does not discard existing data.

#### Scenario: Startup on existing database
- **WHEN** the `fashion_agent` process starts and `llm_token_usage` already exists
- **THEN** startup succeeds without errors or data loss

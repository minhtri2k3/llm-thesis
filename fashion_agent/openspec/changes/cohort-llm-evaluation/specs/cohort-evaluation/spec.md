## ADDED Requirements

### Requirement: Cohort study feature flag

The system SHALL gate all cohort-study behaviour behind the `ENABLE_COHORT_STUDY` environment variable. When the flag is unset or `false`, the system SHALL behave identically to the pre-change implementation. The flag SHALL be readable via a `_is_cohort_study_enabled()` helper modeled on `_is_path2_enabled()`.

#### Scenario: Flag off restores legacy behaviour
- **WHEN** `ENABLE_COHORT_STUDY=false` and a client posts `POST /api/sessions` with `preferred_model="gemini-2.5-flash"`
- **THEN** the request succeeds and the session is created with no `study_group` and no `agent_codename`

#### Scenario: Flag off rejects new model IDs
- **WHEN** `ENABLE_COHORT_STUDY=false` and a client posts `POST /api/sessions` with `preferred_model="gemini-2.5-pro"`
- **THEN** the request is rejected with HTTP 422 (current validator behaviour preserved)

#### Scenario: Flag off cohort dashboard returns 503
- **WHEN** `ENABLE_COHORT_STUDY=false` and a client requests `GET /api/analytics/cohort`
- **THEN** the response is HTTP 503 with `{"detail": "cohort study not enabled"}`

### Requirement: Codename↔model mapping

The system SHALL expose a fixed mapping between four codenames and four Gemini model IDs in `agent/cohort.py`. The mapping SHALL be:

| Codename | Model ID |
|----------|----------|
| Indigo   | gemini-2.5-flash |
| Crimson  | gemini-2.5-pro |
| Emerald  | gemini-3.1-flash-lite |
| Amber    | gemini-3.1-pro-preview |

The mapping SHALL be the single source of truth used by both the assignment logic and the dashboard response.

#### Scenario: Codename resolves to model
- **WHEN** `CODENAME_TO_MODEL["Emerald"]` is read
- **THEN** the value is `"gemini-3.1-flash-lite"`

#### Scenario: Model resolves to codename
- **WHEN** `MODEL_TO_CODENAME["gemini-3.1-pro-preview"]` is read
- **THEN** the value is `"Amber"`

#### Scenario: Mapping exposed verbatim in dashboard
- **WHEN** `GET /api/analytics/cohort` is called with the flag on
- **THEN** the response body contains `"mapping": { "Indigo": "gemini-2.5-flash", "Crimson": "gemini-2.5-pro", "Emerald": "gemini-3.1-flash-lite", "Amber": "gemini-3.1-pro-preview" }`

### Requirement: Latin-square session assignment

When `ENABLE_COHORT_STUDY=true`, the system SHALL assign each tester to one of four groups (round-robin on registration) and SHALL determine each session's codename via a fixed 4×4 Latin square. Each codename SHALL appear in each session position exactly once across the four groups.

The Latin square SHALL be:

| Group   | Session 1 | Session 2 | Session 3 | Session 4 |
|---------|-----------|-----------|-----------|-----------|
| Group1  | Indigo    | Crimson   | Emerald   | Amber     |
| Group2  | Crimson   | Emerald   | Amber     | Indigo    |
| Group3  | Emerald   | Amber     | Indigo    | Crimson   |
| Group4  | Amber     | Indigo    | Crimson   | Emerald   |

#### Scenario: First tester assigned to Group1
- **WHEN** the first tester registers with the flag on
- **THEN** `study_group="Group1"` and the first assigned codename is `"Indigo"`

#### Scenario: Tester returns for second session
- **WHEN** a Group1 tester returns and creates a second session
- **THEN** `agent_codename="Crimson"` is assigned and the model_id is `gemini-2.5-pro`

#### Scenario: Fifth session is rejected
- **WHEN** a tester who has already completed 4 cohort sessions creates a fifth
- **THEN** the API returns HTTP 409 with `{"detail": "cohort study completed for this user"}`

#### Scenario: User does not pick the model
- **WHEN** a tester posts `POST /api/sessions` with `preferred_model="gemini-2.5-flash"` while their next assigned codename is `"Crimson"` (`gemini-2.5-pro`)
- **THEN** the assignment overrides the request; the persisted session has `preferred_model="gemini-2.5-pro"` and `agent_codename="Crimson"`

### Requirement: Startup smoke test for cohort models

When `ENABLE_COHORT_STUDY=true`, the FastAPI application SHALL, during its lifespan startup, attempt one cheap `generate("ping")` call against each of the four Gemini model IDs. Models that fail the test SHALL be added to a module-level `_UNREACHABLE_CODENAMES` set, and `assign_cohort_session()` SHALL skip those codenames. Failures SHALL be logged at ERROR level. The application SHALL continue to start regardless of how many cells failed.

#### Scenario: All four models reachable
- **GIVEN** all 4 model IDs respond to `generate("ping")` within 30 seconds
- **THEN** `_UNREACHABLE_CODENAMES` is empty and assignment proceeds normally

#### Scenario: Preview model unreachable
- **GIVEN** `gemini-3.1-pro-preview` raises `PermissionDenied` at boot
- **THEN** `_UNREACHABLE_CODENAMES = {"Amber"}`, an ERROR log line names the failed codename, and `assign_cohort_session()` skips Amber from rotation

### Requirement: Per-turn latency capture

The system SHALL record three latency measurements per turn into `llm_token_usage`: `intent_latency_ms` (wall-clock around `classify_intent()`), `synthesis_latency_ms` (wall-clock around the synthesis call/stream), and `latency_ms` (wall-clock from `_orchestrate_stream()` entry to final response yield). The columns SHALL default to `0` to preserve compatibility with existing rows and code that does not pass them.

#### Scenario: Latencies recorded for synthesis row
- **WHEN** a chat completes successfully
- **THEN** the `llm_token_usage` row with `call_name='synthesis'` has `latency_ms > 0`, `synthesis_latency_ms > 0`, and `intent_latency_ms == 0` (intent is on its own row)

#### Scenario: Pre-change rows unaffected
- **WHEN** the migration runs on an existing database with pre-change rows
- **THEN** existing rows have `latency_ms = 0`, `intent_latency_ms = 0`, `synthesis_latency_ms = 0` and remain queryable

### Requirement: Cohort dashboard endpoint

When `ENABLE_COHORT_STUDY=true`, the system SHALL expose `GET /api/analytics/cohort` (admin-protected, mirroring `/api/analytics/token-usage`). The endpoint SHALL aggregate per `agent_codename` for sessions with `study_group IS NOT NULL`. The response SHALL include the codename↔model mapping plus, per cell: session count, turn count, average input/output tokens per turn, p50 and p95 of total/intent/synthesis latency, click-through rate, cart adds per session, average rating, and clarification rate.

#### Scenario: Endpoint returns one cell per active codename
- **GIVEN** 4 testers have completed 4 sessions each under the flag
- **WHEN** an admin calls `GET /api/analytics/cohort`
- **THEN** the response contains four cell objects, one per codename, each with `n_sessions >= 1`

#### Scenario: Pre-study legacy rows excluded
- **GIVEN** the database contains 100 pre-change `user_sessions` rows (all with `study_group IS NULL`) and 4 cohort rows
- **WHEN** the dashboard endpoint is called
- **THEN** the cell aggregates reflect only the 4 cohort rows; the legacy 100 are not counted

### Requirement: Existing data preservation

The system SHALL NOT delete, rename, or alter the type of any pre-existing column. All schema changes SHALL be `ADD COLUMN IF NOT EXISTS` and SHALL provide safe defaults so that pre-existing rows remain valid and queryable.

#### Scenario: Legacy session still readable post-migration
- **GIVEN** a `user_sessions` row created before this change with no `study_group`
- **WHEN** the leaderboard endpoint is called
- **THEN** the row is returned with the same fields as before; `study_group` and `agent_codename` are returned as `null`

#### Scenario: Legacy token row still queryable
- **GIVEN** an `llm_token_usage` row created before this change
- **WHEN** `session_token_summary` view is queried
- **THEN** the row contributes to the aggregate and `latency_ms` is reported as `0`

### Requirement: Tester is single-blinded to model identity

In cohort mode, the Flutter frontend SHALL display only the codename to the tester. The backend response on session creation SHALL return the `agent_codename` but the corresponding model ID SHALL NOT appear in any tester-facing UI element. The codename↔model mapping SHALL be visible only in the admin Cohort dashboard and in server logs.

#### Scenario: Tester registration UI hides model
- **WHEN** a tester registers with the flag on
- **THEN** the registration screen shows "You are testing: Indigo" (or the assigned codename) and does NOT show the string "gemini-2.5-flash" anywhere

#### Scenario: Chat screen header shows codename
- **WHEN** a tester opens the chat screen
- **THEN** the header shows the assigned agent codename for that session

## MODIFIED Requirements

### Requirement: Session model validator

The `CreateSessionRequest.preferred_model` validator SHALL accept `gemini-2.5-flash` unconditionally. When `ENABLE_COHORT_STUDY=true` it SHALL additionally accept `gemini-2.5-pro`, `gemini-3.1-flash-lite`, and `gemini-3.1-pro-preview`. Any other value SHALL be rejected with HTTP 422.

#### Scenario: Default model accepted in any mode
- **WHEN** any client posts with `preferred_model="gemini-2.5-flash"`
- **THEN** the request is valid regardless of the flag value

#### Scenario: Cohort model accepted only with flag
- **WHEN** the flag is `true` and a client posts with `preferred_model="gemini-3.1-pro-preview"`
- **THEN** the request is valid

#### Scenario: Cohort model rejected without flag
- **WHEN** the flag is `false` and a client posts with `preferred_model="gemini-3.1-pro-preview"`
- **THEN** the request returns HTTP 422 with the existing message

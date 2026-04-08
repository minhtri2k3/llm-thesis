## ADDED Requirements

### Requirement: Token cost aggregation by orchestration mode
The system SHALL expose `GET /api/analytics/token-costs` returning per-turn token counts and estimated USD cost broken down by `orchestration_mode`, `orchestrator_model`, and `synthesizer_model`.

#### Scenario: Successful cost breakdown response
- **WHEN** client calls `GET /api/analytics/token-costs`
- **THEN** response is HTTP 200 JSON array where each row contains `orchestration_mode`, `orchestrator_model`, `synthesizer_model`, `n_sessions`, `n_turns`, `avg_total_tokens`, `avg_tool_calls`, and `avg_usd_per_turn`

#### Scenario: USD pricing is based on published model family rates
- **WHEN** the endpoint calculates cost
- **THEN** Gemini models use $0.075/1M input and $0.30/1M output, GPT-4o uses $2.50/1M input and $10.00/1M output, Claude 3.5 Sonnet uses $3.00/1M input and $15.00/1M output

#### Scenario: Orchestrator and synthesizer tokens are counted separately
- **WHEN** a turn uses an agentic orchestration mode (Mode B or C)
- **THEN** `orchestrator_input_tokens + orchestrator_output_tokens` are priced at the orchestrator model's rate and `input_tokens + output_tokens` are priced at the synthesizer model's rate

#### Scenario: Direct mode has zero orchestrator cost
- **WHEN** `orchestration_mode = 'direct'` (Mode A)
- **THEN** `orchestrator_input_tokens` and `orchestrator_output_tokens` are both 0 and the entire cost is attributed to the synthesizer (Gemini)

### Requirement: Mode cost summary DB view
The system SHALL maintain a `mode_cost_summary` Postgres view that encapsulates the cost aggregation SQL, queryable by both the API and the analysis notebook.

#### Scenario: View is idempotently created on startup
- **WHEN** the application starts and runs migrations
- **THEN** `mode_cost_summary` view exists in the database and returns correct rows without error

#### Scenario: Adding new sessions updates view results
- **WHEN** new rows are inserted into `llm_token_usage`
- **THEN** subsequent queries to `mode_cost_summary` reflect the updated aggregates

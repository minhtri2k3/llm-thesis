## ADDED Requirements

### Requirement: Agentic overhead ratio tracking
The system SHALL compute Agentic Overhead Ratio per mode as `(orchestrator_input_tokens + orchestrator_output_tokens) / total_tokens_per_turn` for agentic modes (B and C).

#### Scenario: Direct mode has overhead ratio of 0
- **WHEN** `orchestration_mode = 'direct'`
- **THEN** agentic overhead ratio = 0 (no orchestrator tokens)

#### Scenario: Overhead ratio reflects orchestration cost
- **WHEN** a Mode B turn uses 1,200 orchestrator tokens out of 2,000 total
- **THEN** overhead ratio = 0.60 (60% of tokens spent on orchestration)

### Requirement: Tool call efficiency metric
The system SHALL compute Tool Call Efficiency as the average number of products returned per tool call per session: `SUM(result_count from tool_calls_json) / COUNT(tool calls)`.

#### Scenario: Tool efficiency is extracted from JSONB
- **WHEN** `tool_calls_json = [{"tool": "search_fashion", "result_count": 10}, {"tool": "search_fashion", "result_count": 8}]`
- **THEN** tool efficiency for that turn = (10 + 8) / 2 = 9.0 products/call

#### Scenario: Direct mode sessions have efficiency of NULL
- **WHEN** `tool_calls_json = []` (Mode A)
- **THEN** tool efficiency is NULL or omitted for that mode

### Requirement: Tool call diversity metric
The system SHALL compute Tool Call Diversity as the ratio of unique tool names to total tool calls per session.

#### Scenario: All same tool calls gives diversity of 0
- **WHEN** orchestrator calls `search_fashion` 3 times in a session
- **THEN** diversity = 1/3 = 0.33

#### Scenario: Mixed tool calls gives higher diversity
- **WHEN** orchestrator calls `search_fashion` twice and `recommend_outfit` once
- **THEN** diversity = 2/3 = 0.67

### Requirement: Agentic overhead API endpoint
The system SHALL expose `GET /api/analytics/token-costs` to include `avg_tool_calls` and the overhead data needed to compute these metrics in the notebook.

#### Scenario: Tool call count included in cost endpoint
- **WHEN** client calls `GET /api/analytics/token-costs`
- **THEN** response includes `avg_tool_calls` (float) per mode row

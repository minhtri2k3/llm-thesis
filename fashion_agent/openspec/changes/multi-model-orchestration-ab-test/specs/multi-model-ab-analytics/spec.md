## ADDED Requirements

### Requirement: Orchestration mode tracking per turn
The system SHALL record the orchestration mode, orchestrator model, synthesizer model, and tool call sequence for every conversation turn in `conversation_events`.

New columns in `conversation_events`:
- `orchestration_mode TEXT` — `"direct"` | `"agentic"`
- `orchestrator_model TEXT` — model ID used as orchestrator (or `"fixed"` for Mode A)
- `synthesizer_model TEXT` — model ID used for synthesis
- `tool_calls_json JSONB` — array of tool calls made by orchestrator: `[{tool, args, result_count, duration_ms}]`

#### Scenario: Mode A turn recorded
- **WHEN** a Gemini session processes a turn
- **THEN** `orchestration_mode = "direct"`, `orchestrator_model = "fixed"`, `synthesizer_model = "gemini-*"`, `tool_calls_json = []`

#### Scenario: Mode B turn with search recorded
- **WHEN** a GPT session processes a turn and Gemini orchestrator calls `search_fashion`
- **THEN** `orchestration_mode = "agentic"`, `orchestrator_model = "gemini-*"`, `synthesizer_model = "gpt-*"`, `tool_calls_json = [{"tool": "search_fashion", "args": {...}, "result_count": 12, "duration_ms": 340}]`

#### Scenario: Mode C turn with fallback recorded
- **WHEN** a Claude session falls back to direct routing due to orchestrator failure
- **THEN** `orchestration_mode = "direct"`, with `tool_calls_json = [{"tool": "fallback", "reason": "orchestrator_unavailable"}]`

---

### Requirement: Gender hint status tracked per session
The system SHALL expose `gender_hint_enabled` in analytics queries to support A/B analysis of gender prompting effect.

#### Scenario: Gender A/B analytics query
- **WHEN** a researcher queries the analytics endpoint
- **THEN** the response SHALL include per-session `gender_hint_enabled` status correlatable with satisfaction ratings and selection data

---

### Requirement: Token cost recorded per turn
The system SHALL record input and output token counts for both orchestrator and synthesizer calls in Mode B and C sessions, stored alongside the existing token tracking in `conversation_events`.

#### Scenario: Mode B token costs tracked separately
- **WHEN** a GPT session turn completes
- **THEN** `conversation_events` SHALL record `orchestrator_input_tokens`, `orchestrator_output_tokens`, `synthesizer_input_tokens`, `synthesizer_output_tokens` from the respective API usage metadata

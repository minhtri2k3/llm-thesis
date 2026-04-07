## ADDED Requirements

### Requirement: Three-mode orchestration routing
The system SHALL determine orchestration mode from `user_sessions.preferred_model` at session start and apply it for all turns in that session:
- `gemini-*` → **Mode A**: Direct routing (fixed `_route_and_execute()`), Gemini synthesizes
- `gpt-*` → **Mode B**: Gemini agentic orchestrator (tool-calling loop), GPT-4o synthesizes
- `claude-*` → **Mode C**: GPT-4o agentic orchestrator (tool-calling loop), Claude synthesizes

#### Scenario: Gemini session uses direct routing
- **WHEN** `preferred_model` starts with `"gemini"`
- **THEN** the system SHALL use the existing `_route_and_execute()` and Gemini for synthesis (no orchestration overhead)

#### Scenario: GPT session uses Gemini orchestrator
- **WHEN** `preferred_model` starts with `"gpt"`
- **THEN** the system SHALL invoke the Gemini agentic orchestrator, execute tools based on its decisions, then pass results to GPT-4o for synthesis

#### Scenario: Claude session uses GPT orchestrator
- **WHEN** `preferred_model` starts with `"claude"`
- **THEN** the system SHALL invoke the GPT-4o agentic orchestrator, execute tools based on its decisions, then pass results to Claude for synthesis

---

### Requirement: Agentic orchestrator tool-calling loop
For Modes B and C, the orchestrator model SHALL receive a set of declared tools and decide which to call via native function/tool calling API. Available tools:
- `search_fashion(query: str, category: str|null, color: str|null, style: str|null)` — runs hybrid search
- `ask_clarification(question: str)` — returns a clarification question to the user (terminates the loop for this turn)
- `get_user_selections(session_id: str)` — retrieves current cart items
- `save_selections(session_id: str, item_numbers: list[int])` — saves selected items

#### Scenario: Orchestrator decides to search
- **WHEN** user sends a search intent query in a Mode B or C session
- **THEN** the orchestrator SHALL call `search_fashion` with appropriate parameters extracted from the query

#### Scenario: Orchestrator decides to clarify
- **WHEN** the query is ambiguous and the orchestrator determines clarification is needed
- **THEN** the orchestrator SHALL call `ask_clarification` and the loop SHALL terminate, returning the question to the user

#### Scenario: Tool call cap enforced
- **WHEN** the orchestrator has made 5 tool calls in a single turn
- **THEN** the system SHALL stop the loop and proceed to synthesis with results collected so far

#### Scenario: Orchestrator API unavailable
- **WHEN** the orchestrator model API returns an error (5xx or timeout)
- **THEN** the system SHALL fall back to Mode A direct routing for that turn and log a `fallback_to_direct_routing` event

---

### Requirement: Synthesis receives tool results as context
For Modes B and C, the synthesis model SHALL receive the orchestrator's tool call results (search results, clarification decisions) as structured context in the synthesis prompt, in place of the direct-routing search results.

#### Scenario: Search results passed to synthesizer
- **WHEN** the orchestrator calls `search_fashion` and receives results
- **THEN** those results SHALL be included in the synthesis prompt under a `Tool Results` section, indistinguishable in format from the existing search results format

#### Scenario: Synthesis model has no tool access
- **WHEN** synthesis model is invoked
- **THEN** it SHALL NOT have access to any tool declarations — it produces only a text response

## ADDED Requirements

### Requirement: Model picker at registration
The registration screen SHALL display three selectable options: "Gemini 2.5 Flash", "GPT-4o", and "Claude 3.5 Sonnet". Exactly one MUST be selected before the user can start a session. The selected model's ID (`gemini-2.5-flash`, `gpt-4o`, `claude-3-5-sonnet-20241022`) SHALL be sent in `POST /api/sessions` as `preferred_model`.

#### Scenario: Default model pre-selected
- **WHEN** the registration screen loads
- **THEN** "Gemini 2.5 Flash" is pre-selected

#### Scenario: User submits form with model selected
- **WHEN** user selects "GPT-4o" and taps "Start"
- **THEN** `POST /api/sessions` body contains `"preferred_model": "gpt-4o"`

#### Scenario: Model selection required
- **WHEN** user attempts to start without selecting a model (if no default)
- **THEN** an error message is shown and submission is blocked

### Requirement: Session stores preferred model
The backend `POST /api/sessions` endpoint SHALL accept `preferred_model: str` (default `"gemini-2.5-flash"`). `create_session()` SHALL validate `preferred_model` is in the allowlist and store it in `user_sessions.preferred_model`.

#### Scenario: Valid model stored
- **WHEN** `POST /api/sessions` is called with `preferred_model: "gpt-4o"`
- **THEN** `user_sessions.preferred_model = "gpt-4o"` for the created session

#### Scenario: Invalid model defaults to Gemini
- **WHEN** `POST /api/sessions` is called with an unknown `preferred_model`
- **THEN** the session is created with `preferred_model = "gemini-2.5-flash"`

### Requirement: Agent uses session's preferred model
At the start of each `_orchestrate_stream()` call, the system SHALL retrieve `user_sessions.preferred_model` and call `get_client(preferred_model)` to obtain the LLM client for that request.

#### Scenario: GPT-4o session uses OpenAI client
- **WHEN** a chat message is sent for a session with `preferred_model = "gpt-4o"`
- **THEN** synthesis is performed via `OpenAIClient` and token usage is logged with `model_name = "gpt-4o"`

## ADDED Requirements

### Requirement: Session model selection SHALL be Gemini-only
The system SHALL accept only `gemini-2.5-flash` as `preferred_model` when creating chat sessions. Any other model identifier MUST be rejected with a validation error.

#### Scenario: Create session with Gemini model
- **WHEN** a client sends `POST /api/sessions` with `preferred_model = "gemini-2.5-flash"`
- **THEN** the system creates the session successfully

#### Scenario: Create session with deprecated model
- **WHEN** a client sends `POST /api/sessions` with `preferred_model = "gpt-4o"` or `preferred_model = "claude-3-7-sonnet-latest"`
- **THEN** the system rejects the request with a validation error that indicates the allowed model value

### Requirement: Chat execution SHALL use direct non-agentic orchestration
The system SHALL execute chat requests through the direct orchestration path only. Agentic orchestration mode MUST NOT be selected at runtime.

#### Scenario: Stream chat response
- **WHEN** a client sends `POST /api/chat/stream` for a valid session
- **THEN** the system processes intent, retrieval, and synthesis without entering agentic orchestration steps

#### Scenario: Emit orchestration metadata
- **WHEN** the chat stream reaches completion
- **THEN** the system emits completion metadata consistent with direct execution mode

### Requirement: Frontend SHALL not offer deprecated model choices
The frontend registration/chat-entry UI SHALL only present the Gemini model option and SHALL submit that value when creating a session.

#### Scenario: User starts a new chat session
- **WHEN** a user opens the registration/start-chat screen
- **THEN** the model selector does not show GPT-4o or Claude options
- **AND** session creation sends `preferred_model = "gemini-2.5-flash"`

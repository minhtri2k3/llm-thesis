## MODIFIED Requirements

### Requirement: Model selection determines orchestration strategy
Model selection (captured at session creation in `user_sessions.preferred_model`) SHALL determine not only the synthesis model but also the orchestration mode and orchestrator model for all turns in the session. The mapping is fixed:

| Selected Model | Orchestration Mode | Orchestrator | Synthesizer |
|---------------|-------------------|--------------|-------------|
| `gemini-*`    | Direct (Mode A)    | Fixed routing | Gemini      |
| `gpt-*`       | Agentic (Mode B)   | Gemini        | GPT-4o      |
| `claude-*`    | Agentic (Mode C)   | GPT-4o        | Claude      |

#### Scenario: Gemini selected at registration
- **WHEN** user selects a Gemini model during session creation
- **THEN** all turns in that session SHALL use Mode A (direct routing + Gemini synthesis)

#### Scenario: GPT selected at registration
- **WHEN** user selects a GPT model during session creation
- **THEN** all turns in that session SHALL use Mode B (Gemini orchestrator + GPT synthesis)

#### Scenario: Claude selected at registration
- **WHEN** user selects a Claude model during session creation
- **THEN** all turns in that session SHALL use Mode C (GPT-4o orchestrator + Claude synthesis)

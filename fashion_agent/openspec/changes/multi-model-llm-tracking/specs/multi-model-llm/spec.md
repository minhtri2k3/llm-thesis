## ADDED Requirements

### Requirement: Unified LLM client abstraction
The system SHALL expose a `LLMClient` protocol in `shared/llm.py` with `model_name: str`, `generate(prompt) -> str`, and `stream(prompt) -> Generator` methods. Three concrete implementations SHALL exist: `GeminiClient`, `OpenAIClient`, and `AnthropicClient`. A factory function `get_client(model_id: str) -> LLMClient` SHALL dispatch by model ID prefix (`gemini-*`, `gpt-*`, `claude-*`). Unknown prefixes SHALL default to `GeminiClient`.

#### Scenario: Gemini model routed correctly
- **WHEN** `get_client("gemini-2.5-flash")` is called
- **THEN** a `GeminiClient` instance is returned with `model_name == "gemini-2.5-flash"`

#### Scenario: GPT model routed correctly
- **WHEN** `get_client("gpt-4o")` is called
- **THEN** an `OpenAIClient` instance is returned with `model_name == "gpt-4o"` and it uses `GPT_API_KEY` from env

#### Scenario: Claude model routed correctly
- **WHEN** `get_client("claude-3-5-sonnet-20241022")` is called
- **THEN** an `AnthropicClient` instance is returned with `model_name == "claude-3-5-sonnet-20241022"` and it uses `ANTHROPIC_API_KEY` from env

#### Scenario: Unknown model ID defaults to Gemini
- **WHEN** `get_client("unknown-model")` is called
- **THEN** a `GeminiClient` with default model is returned (no exception)

### Requirement: Correct model name in token logs
The system SHALL use the active session's `LLMClient.model_name` when calling `log_token_usage()`. Hardcoded `"gemini-2.5-flash"` strings in `fashion_agent.py` SHALL be removed.

#### Scenario: Token log reflects actual provider
- **WHEN** a session uses `gpt-4o` and completes a synthesis call
- **THEN** `llm_token_usage.model_name = "gpt-4o"` is recorded for that call

#### Scenario: Missing API key raises RuntimeError on first call
- **WHEN** `AnthropicClient.stream()` is called but `ANTHROPIC_API_KEY` is not set
- **THEN** a `RuntimeError` is raised with a descriptive message; server does not crash on startup

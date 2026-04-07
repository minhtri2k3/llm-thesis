## Why

The Fashion Agent currently uses a single fixed orchestration strategy (deterministic routing) and ignores user demographics (gender) in its prompts, limiting recommendation personalization and research value. Additionally, language detection has a known regression where English queries can produce Spanish responses. This change evolves the system into a **multi-model A/B research platform** that tests orchestration quality, synthesis language model quality, and demographic-aware prompting simultaneously — all within the constraints of the existing model selection flow.

## What Changes

- **Gender-aware prompting**: User gender (stored in `user_sessions.gender`) is fetched and injected into the synthesis prompt so the LLM can personalize recommendations by gender (e.g., menswear vs. womenswear).
- **Gender measurement A/B control**: A session-level flag (`gender_hint_enabled`) is randomly assigned (50/50) at session creation time, enabling post-hoc comparison of recommendation alignment with and without the gender hint.
- **Language detection fix**: The `detect_language()` regex is tightened to eliminate false positives on English text; language is also passed as an explicit mandatory instruction to the synthesis prompt (`YOU MUST respond in {language}`), making it immune to history contamination.
- **Three-mode orchestration**: The selected model (`preferred_model`) determines the *orchestration + synthesis pairing*:
  - **Gemini** → Mode A: Direct routing (current), Gemini synthesizes (no orchestrator overhead)
  - **GPT-4o** → Mode B: Gemini acts as agentic orchestrator (tool-calling loop), GPT-4o synthesizes
  - **Claude** → Mode C: GPT-4o acts as agentic orchestrator (tool-calling loop), Claude synthesizes
- **Orchestrator tool-calling loop**: For Modes B and C, the orchestrator model receives a set of declared tools (`search_fashion`, `ask_clarification`, `get_selections`, `save_selections`) and decides which to call and in what order, replacing the fixed `_route_and_execute()` logic for those sessions.
- **Analytics schema extension**: New columns in `conversation_events` to track orchestration mode, orchestrator model, synthesizer model, tool calls made, and turn token costs per session — enabling cross-mode comparison in the leaderboard.

## Capabilities

### New Capabilities

- `gender-aware-prompting`: Injects user gender into synthesis prompt with 50/50 A/B control group (hint vs. no-hint) to measure recommendation alignment
- `language-detection-fix`: Tightened Spanish regex + explicit language variable in synthesis prompt to eliminate cross-language contamination
- `agentic-orchestration-mode`: Orchestrator tool-calling loop (using Gemini or GPT-4o) that replaces fixed routing for Mode B and C sessions
- `multi-model-ab-analytics`: Schema and metrics tracking orchestration mode, model pairing, tool call sequences, and turn costs for research comparison

### Modified Capabilities

- `model-selection`: Existing model selection now also determines orchestration strategy (Mode A/B/C), not just synthesis model

## Impact

**Code files:**
- `agent/fashion_agent.py` — new `_agentic_orchestrate()` method, modified `chat()` to branch by mode, modified `_build_synthesis_context()` for gender + language
- `agent/prompts.py` — tightened `detect_language()`, updated `_BASE_SYNTHESIS_PROMPT` with `{language}` and `{gender_context}` variables
- `agent/memory.py` — add `get_session_gender()` helper, add `gender_hint_enabled` field to session, analytics schema migration
- `api/main.py` — session creation assigns `gender_hint_enabled` randomly

**New dependencies:**
- Gemini native function calling (`genai.GenerativeModel(tools=[...])`) — already in `google-generativeai` SDK
- OpenAI function calling — already supported in existing `OpenAIClient`

**Database:**
- Migration: add `gender_hint_enabled BOOLEAN` to `user_sessions`
- Migration: add `orchestration_mode TEXT`, `orchestrator_model TEXT`, `synthesizer_model TEXT` columns to `conversation_events`

**No breaking changes** — all changes are additive or conditional on model selection.

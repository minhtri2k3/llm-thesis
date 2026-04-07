## 1. Database Migrations

- [x] 1.1 Add `gender_hint_enabled BOOLEAN NOT NULL DEFAULT FALSE` column to `user_sessions` table
- [x] 1.2 Add `orchestration_mode TEXT`, `orchestrator_model TEXT`, `synthesizer_model TEXT` columns to `conversation_events` table
- [x] 1.3 Add `tool_calls_json JSONB DEFAULT '[]'` column to `conversation_events` table
- [x] 1.4 Add `orchestrator_input_tokens INT`, `orchestrator_output_tokens INT` columns to `conversation_events` table
- [x] 1.5 Verify migrations apply cleanly on existing database (run on Docker Compose postgres)

## 2. Language Detection Fix

- [x] 2.1 Update `detect_language()` in `agent/prompts.py` — remove ambiguous Spanish words (`el`, `la`, `los`, `las`, `un`, `una`, `es`, `son`) from the regex pattern
- [x] 2.2 Keep only unambiguous Spanish tokens: `ñ`, `¿`, `¡`, `quiero`, `necesito`, `busco`, `vestido`, `ropa`, `cómo`, `gracias`, `hola`, `tengo`
- [x] 2.3 Add `{language}` variable to `_BASE_SYNTHESIS_PROMPT` with mandatory instruction: `"YOU MUST respond exclusively in {language}."`
- [x] 2.4 Thread `language` and `gender_context` variables through all callers via `_build_synthesis_context()`
- [ ] 2.5 Run `test_multilingual_keywords.py` to verify no regressions in language detection

## 3. Gender-Aware Prompting

- [x] 3.1 Add `get_session_gender()` helper to `agent/memory.py` — queries `user_sessions.gender` and `user_sessions.gender_hint_enabled` by `session_id`
- [x] 3.2 Update `create_session()` in `agent/memory.py` to randomly assign `gender_hint_enabled` (50/50 using `random.random() < 0.5`)
- [x] 3.3 Add `{gender_context}` variable to `_BASE_SYNTHESIS_PROMPT` — when populated, inserts `"User profile: gender = {gender}. Prioritize {menswear|womenswear} appropriate items."`
- [x] 3.4 Update `_build_synthesis_context()` in `agent/fashion_agent.py` to call `get_session_gender()` and populate `gender_context` based on `gender_hint_enabled`
- [x] 3.5 When `gender_hint_enabled = FALSE` or gender is NULL, pass `gender_context = ""` (empty string, no mention of gender)

## 4. Mode Routing Infrastructure

- [x] 4.1 Create `_get_orchestration_mode(preferred_model: str)` helper in `agent/fashion_agent.py` returning `("direct", "fixed", model_id)` or `("agentic", orchestrator_model, model_id)`
- [x] 4.2 Mode routing: `gpt-*` → Gemini orchestrates + GPT synthesizes; `claude-*` → GPT orchestrates + Claude synthesizes; `gemini-*` → direct
- [x] 4.3 Modify `chat_stream()` to branch on orchestration mode: Mode A calls existing synthesis, Modes B/C call agentic orchestration
- [x] 4.4 Mode detection uses prefix matching: `model_id.startswith("gpt-")`, `model_id.startswith("claude-")`

## 5. Agentic Orchestration Loop

- [x] 5.1 Created `agent/agentic_orchestrator.py` with `ORCHESTRATOR_TOOLS` for `search_fashion` and `recommend_outfit` (both Gemini and OpenAI schemas)
- [x] 5.2 Implement `orchestrate_with_gemini()` — Gemini native function calling loop (4-iteration hard cap)
- [x] 5.3 Implement `orchestrate_with_gpt()` — GPT-4o native function calling loop (4-iteration hard cap)
- [x] 5.4 Implement tool call dispatch (`search_fashion` → `run_search_tool`, `recommend_outfit` → `run_recommend_tool`) in `agent/tools.py`
- [x] 5.5 Implement 4-iteration hard cap: after 4 tool calls, break loop and synthesize with available results
- [x] 5.6 Both orchestrators return `AgenticOrchestrationResult` with `products`, `tool_results_text`, `tool_calls`, token counts
- [x] 5.7 Fallback: if orchestrator API raises exception → log error, set `error` field, return partial result with empty tool_results_text

## 6. Synthesis Integration for Agentic Modes

- [x] 6.1 Create `STREAM_SYNTHESIS_PROMPT_AGENTIC` in `agent/prompts.py` — accepts `tool_results` instead of `products_text`
- [x] 6.2 After orchestration loop, package tool results + context → call synthesizer via stream
- [x] 6.3 Synthesizer called with no tool declarations (pure text generation)
- [x] 6.4 Synthesis streaming works for all three modes — direct uses `_synthesize_response_stream()`, agentic uses `synth_client.stream()` directly

## 7. Analytics Logging

- [x] 7.1 Updated `log_token_usage()` in `agent/memory.py` to accept and persist `orchestration_mode`, `orchestrator_model`, `synthesizer_model`, `tool_calls_json`
- [x] 7.2 After agentic loop, build `tool_calls_json` list from `AgenticOrchestrationResult.tool_calls` (each entry: `{tool, args, result_count, duration_ms}`)
- [x] 7.3 For Mode A (direct routing), `tool_calls_for_log = []` and `orchestration_mode = "direct"`, `orchestrator_model = "fixed"`
- [x] 7.4 Orchestrator token counts logged separately: `orchestrator_input_tokens`, `orchestrator_output_tokens`

## 8. Testing & Verification

- [x] 8.1 Write `test_language_fix.py` — assert English queries never produce `detect_language()` → `"es"` for a set of 10 ambiguous English phrases (**6 tests, all PASS**)
- [x] 8.2 Write `test_gender_prompt.py` — assert synthesis prompt contains gender block when `gender_hint_enabled=True` and is absent when `False` (**7 tests, all PASS**)
- [x] 8.3 Write `test_orchestration_modes.py` — mock LLM clients, assert Mode A uses fixed router, Mode B uses Gemini tool-calling, Mode C uses OpenAI tool-calling (**13 tests, all PASS**)
- [ ] 8.4 Run existing `test_chat.py` and `test_search.py` to verify Mode A (Gemini) has no regression
- [ ] 8.5 Manual smoke test: create a GPT session, send a search query, verify Gemini orchestrator tool call is logged in `conversation_events.tool_calls_json`
- [ ] 8.6 Manual smoke test: create a Claude session, verify GPT-4o orchestrator is used and Claude produces the final response

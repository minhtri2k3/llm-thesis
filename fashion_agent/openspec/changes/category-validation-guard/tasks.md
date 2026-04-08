## 1. Dependencies & Constants

- [ ] 1.1 Add `rapidfuzz` to `pyproject.toml` under project dependencies
- [ ] 1.2 Add `SUPPORTED_CATEGORIES` set (17 DB labels) to `agent/utils.py`
- [ ] 1.3 Add `UNSUPPORTED_CATEGORY_SUGGESTIONS` static dict to `agent/utils.py`
- [ ] 1.4 Implement `_find_category_suggestions(category: str) -> list[str]` in `agent/utils.py` (static map → rapidfuzz fallback → empty list)

## 2. Multilingual Refusal Messages

- [ ] 2.1 Add `UNSUPPORTED_CATEGORY_RESPONSE` dict to `agent/prompts.py` with EN, VI, ES templates (mirrors `OUT_OF_SCOPE_RESPONSE` pattern)
- [ ] 2.2 Add helper `build_unsupported_category_message(category: str, suggestions: list[str], lang: str) -> str` in `agent/prompts.py`

## 3. Mode A Guard (Non-Streaming)

- [ ] 3.1 In `_resolve_search_query()` in `fashion_agent.py`, add category validation AFTER slot merging and BEFORE slot completeness check
- [ ] 3.2 If `slot_category` is non-empty and not in `SUPPORTED_CATEGORIES`, build refusal message and set `clarification` on the result — return early before any search

## 4. Mode B/C Pre-Flight Guard (Streaming)

- [ ] 4.1 In `chat_stream()` in `fashion_agent.py`, add a pre-flight check AFTER `_orchestrate_stream()` returns `OrchestrateResult` and BEFORE the `if orch_mode == "agentic":` branch
- [ ] 4.2 Extract the detected `slot_category` from `result.filters` (or `result.intent_result`)
- [ ] 4.3 If category is invalid, emit `event: clarification` SSE with the refusal message, then emit `event: done` and return — skip the agentic orchestrator entirely

## 5. Safety-Net in run_search_tool

- [ ] 5.1 In `run_search_tool()` in `agent/tools.py`, import `SUPPORTED_CATEGORIES` and `_find_category_suggestions` from `agent/utils.py`
- [ ] 5.2 After filters are built, if `category` is non-empty and not in `SUPPORTED_CATEGORIES`, return `[{"__error__": "unsupported_category", "requested": category, "suggestions": _find_category_suggestions(category)}]`

## 6. Rebuild & Smoke Testing

- [ ] 6.1 Rebuild Docker container: `docker compose up -d --build fashion-api`
- [ ] 6.2 Smoke test Mode A (Gemini direct): send "find me a bikini" — expect refusal with suggestions, no products returned
- [ ] 6.3 Smoke test Mode B (GPT synthesizer): switch model to GPT-4o, send "find me a bikini" — expect same refusal
- [ ] 6.4 Smoke test Mode C (Claude synthesizer): switch model to Claude, send "find me a bikini" — expect same refusal
- [ ] 6.5 Regression test: send "find me a red dress" — expect normal search results in all three modes
- [ ] 6.6 Test Vietnamese: send "tìm cho tôi áo bikini" — expect Vietnamese-language refusal with suggestions

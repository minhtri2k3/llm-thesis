## Why

The Fashion Agent is a multilingual research instrument (Vietnamese + English + Spanish) but four critical defects break the user experience and invalidate research data: the rejection flow leaves users stranded with no path to pick alternative products; all clarification and confirmation messages are hardcoded English (ignoring the user's language); the LLM's call-to-action CTA is guided by an English example that GPT models follow literally; and the agent's system persona does not explain the research purpose, limiting its ability to guide users toward the selection behavior that drives the thesis data pipeline.

## What Changes

- **Fix rejection flow**: After a user rejects a selection, re-surface the 6 cached results and allow immediate re-selection without a new search. Clear stale pending state when user sends a non-keyword free-text while pending.
- **Fix hardcoded English messages**: Replace hardcoded English strings in `FALLBACK_QUESTION`, `SLOT_TEMPLATES`, `COMBO_TEMPLATES`, and all fixed agent responses (`_handle_reject`, `_handle_confirm`, `_handle_view_selections`, `OUT_OF_SCOPE_RESPONSE`) with language-aware variants that detect Vietnamese vs English from the user's message.
- **Fix CTA language in synthesis prompt**: Strengthen the synthesis instruction so GPT/Gemini models reliably write the call-to-action in the user's language (provide explicit multilingual examples, not just an adapt hint).
- **Update agent persona in prompts**: Update `INTENT_PROMPT` and `_BASE_SYNTHESIS_PROMPT` so the LLM understands it is part of a fashion recommendation research system, encouraging product selection for behavioral data collection.

## Capabilities

### New Capabilities

- `multilingual-agent-messages`: All hardcoded agent response strings detect user language (Vietnamese/English/Spanish) and respond accordingly — eliminates all static English-only user-facing text.
- `selection-reject-recovery`: After rejection, agent re-displays cached results summary and invites re-selection — user can immediately pick a different number without searching again.
- `research-aware-agent-persona`: System prompts convey the LLM's role in a multilingual fashion recommendation research study, improving coherence of agent behavior toward the thesis goal.

### Modified Capabilities

*(No existing OpenSpec specs to delta — no `openspec/specs/` directory present.)*

## Impact

- **`fashion_agent/agent/prompts.py`** — `INTENT_PROMPT`, `_BASE_SYNTHESIS_PROMPT`, `FALLBACK_QUESTION`, `SLOT_TEMPLATES`, `COMBO_TEMPLATES`
- **`fashion_agent/agent/fashion_agent.py`** — `_handle_reject()`, `_handle_confirm()`, `_handle_view_selections()`, `_handle_product_select()`, `OUT_OF_SCOPE_RESPONSE`, `_orchestrate_stream()` pending-state fall-through
- **`fashion_agent/agent/clarification_gate.py`** — `check_clarification()` fallback path
- **No API changes, no DB schema changes, no Flutter changes** — purely agent logic and prompt layer

## 1. Utilities and Prompt Context

- [x] 1.1 Implement `detect_language(text: str) -> str` utility using regex for Vietnamese diacritics
- [x] 1.2 Prepend research-context paragraph and multilingual constraint to `INTENT_PROMPT`
- [x] 1.3 Prepend research-context paragraph and multilingual constraint to `_BASE_SYNTHESIS_PROMPT`
- [x] 1.4 Update synthesis prompt to use `{cta_example}` format variable instead of hardcoded English CTA

## 2. Bilingual Templates and Clarification

- [x] 2.1 Convert `FALLBACK_QUESTION` to a bilingual structure
- [x] 2.2 Convert `COMBO_TEMPLATES` and `SLOT_TEMPLATES` to bilingual structures and implement a `_t(key, lang)` helper
- [x] 2.3 Update `check_clarification()` in `clarification_gate.py` to use `detect_language()` and return the bilingual `FALLBACK_QUESTION`

## 3. Agent Response Handlers (`fashion_agent.py`)

- [x] 3.1 Make `OUT_OF_SCOPE_RESPONSE` bilingual and update its usage to detect language
- [x] 3.2 Update `_handle_confirm()` to detect language and save response in the correct language
- [x] 3.3 Update `_handle_view_selections()` to return bilingual fallback messages
- [x] 3.4 Update `_handle_product_select()` validation error (invalid index) to be language-aware
- [x] 3.5 Inject `cta_example` (VI or EN) into `_build_synthesis_context()` prior to LLM call

## 4. Selection Reject Recovery (`fashion_agent.py`)

- [x] 4.1 Update `_handle_reject()` to detect user language and confirm cancellation
- [x] 4.2 In `_handle_reject()`, safely fetch `_session_last_results` and append a language-aware compact numbered summary of cached items
- [x] 4.3 In `_orchestrate_stream()`, clear pending state if the user message is a non-keyword free-text message

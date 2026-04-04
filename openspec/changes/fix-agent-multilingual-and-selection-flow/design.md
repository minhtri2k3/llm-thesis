## Context

The Fashion Agent is a multilingual LLM-backed fashion recommendation system serving as the core data-collection instrument for an LLM benchmarking thesis. It supports Vietnamese and English users. The pipeline is: prompt → intent classify → slot gate → search → synthesis → product display → selection. Four defects break this pipeline: (1) the rejection sub-flow leaves users without a recovery path, (2) all hardcoded agent response strings are English regardless of user language, (3) the synthesis CTA is GPT-model-dependent due to an English example string, (4) the LLM system persona is too generic and does not guide toward research-specific behavior.

**Relevant modules**: `agent/prompts.py`, `agent/fashion_agent.py`, `agent/clarification_gate.py`, `agent/slot_completeness.py`

## Goals / Non-Goals

**Goals:**
- After rejection, agent re-shows cached product list and invites re-selection in one turn
- All fixed-string user-facing text detects user language (Vietnamese vs English) before responding
- Synthesis CTA reliably renders in user's language across GPT-4o, Gemini, and Claude
- Intent and synthesis system prompts convey the research context and selection-encouragement goal
- Zero new LLM calls added — changes must be zero-cost or single-call at most
- No breaking changes to the SSE event schema or Flutter API contract

**Non-Goals:**
- Full i18n framework (not adding gettext/babel — detect-and-branch is sufficient for VI/EN)
- Supporting more than 2 languages (only VI and EN in scope for thesis)
- Changing the search ranking, embedding, or retrieval logic
- Modifying the Flutter frontend or API routes

## Decisions

### D1 — Language Detection: regex heuristic over LLM call

**Decision**: Detect Vietnamese from user message using a fast regex (presence of diacritics `[àáảãạăắặẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]` or Vietnamese-pattern words).

**Alternatives considered**:
- *LLM language detect call*: too expensive (extra LLM call per turn), and unnecessary — the intent classifier already operates on the message, which has the text.
- *Accept-Language HTTP header*: not available inside the agent layer without refactor.
- *User profile language setting*: would require schema change and registration UI update.

**Rationale**: A one-line regex that checks for Vietnamese diacritics is deterministic, zero-cost, and ~99% accurate for VI vs EN. Edge cases (e.g., romanized Vietnamese) fall back to English safely.

---

### D2 — COMBO_TEMPLATES / SLOT_TEMPLATES: bilingual dict approach

**Decision**: Each template in `COMBO_TEMPLATES` and `SLOT_TEMPLATES` becomes two variants — one English, one Vietnamese — stored in a bilingual dict keyed by `frozenset` + language. A helper `_t(key, lang)` returns the correct string.

**Alternatives considered**:
- *LLM-translated clarification*: delegates all clarification to LLM — correct but removes the "zero LLM calls" advantage of the slot completeness path.
- *Single prompt with language instruction*: clarification prompts already do this but were not working for hardcoded fallbacks.

**Rationale**: The slot-completeness path's entire value proposition is zero LLM calls. Moving templates to bilingual dicts preserves that while fixing the language bug.

---

### D3 — Reject recovery: re-show cached list, no extra search

**Decision**: `_handle_reject()` reads `_session_last_results[session_id]` and appends a compact summary of the 6 cached items to the rejection message so users can immediately type a different number.

**Alternatives considered**:
- *Auto-trigger a new search*: would require knowing what query to re-run; adds complexity and a full LLM call.
- *Just say "search again"*: current behavior — user is stranded if they just want a different number from the same set.

**Rationale**: The user already saw these 6 items. Redisplaying a compact numbered list (label + color, no images) is a pure string operation — zero LLM calls — and immediately unblocks re-selection.

---

### D4 — CTA language in synthesis: multilingual example injection

**Decision**: Replace the single English CTA example in `_BASE_SYNTHESIS_PROMPT` with explicit VI and EN examples and a strict instruction that prohibits English if user is Vietnamese.

**Alternatives considered**:
- *Post-process the streamed response to append CTA*: fragile, breaks streaming coherence.
- *Hard-code CTA outside LLM*: would require parsing where LLM text ends.

**Rationale**: Prompt engineering fix — no code change in the synthesis path, just prompt text. The root cause is that LLMs anchor on provided examples; giving a VI example when user is VI cuts the problem at source. Since the synthesis prompt is already formatted with `query` context, we can inject `cta_example` as a format variable that pre-selects the correct language CTA string in Python before the LLM call.

---

### D5 — Research persona: prefix paragraph, not system-message rewrite

**Decision**: Prepend a concise research-context paragraph to both `INTENT_PROMPT` and `_BASE_SYNTHESIS_PROMPT` rather than restructuring the entire prompt.

**Rationale**: Minimal change surface — existing few-shot examples and instructions remain intact. The prefix provides enough context for the LLM to adjust tone and encourage selection behavior.

## Risks / Trade-offs

- **[Risk] Regex false positives on mixed-language text** → Mitigation: only use the regex to choose *template language*; if uncertain, default to English (safer for research data legibility).
- **[Risk] Reject-recovery list grows stale** → Mitigation: `_session_last_results` has a 30-min TTL already; if cache is empty, fall back to "please search again" message gracefully.
- **[Risk] CTA format variable injection changes prompt format string** → Mitigation: `_build_synthesis_context()` already returns a dict; add `cta_example` key there with no downstream contract change.
- **[Risk] Research persona paragraph confuses intent classification** → Mitigation: keep persona paragraph above the intent list, clearly separated; run intent classification smoke tests post-change.

## Migration Plan

1. Update `prompts.py` first (no runtime impact — string changes only)
2. Update `fashion_agent.py` handlers (touches live session cache logic — unit-test before deploy)
3. Update `clarification_gate.py` fallback (trivial — one string reference)
4. Restart the FastAPI server — no DB migration required
5. Rollback: revert the 3 files; no state cleanup needed (all changes are stateless prompt/string logic)

## Open Questions

- *(none)* — all decisions are resolved above

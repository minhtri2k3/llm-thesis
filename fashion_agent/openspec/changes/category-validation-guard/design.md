## Context

The fashion agent supports three orchestration modes:
- **Mode A (Direct, Gemini)**: Gemini classifies intent → slot gate → deterministic router → search
- **Mode B (Agentic, GPT-4o)**: Gemini orchestrates tool calls → GPT-4o synthesizes
- **Mode C (Agentic, Claude)**: GPT-4o orchestrates tool calls → Claude synthesizes

The current flow has **no category validation**. When a user asks for "bikini" (not in the DB), all three modes silently search and return semantically-adjacent but irrelevant results. The 17 valid DB labels are: Blazer, Blouse, Body, Dress, Hat, Hoodie, Longsleeve, Outwear, Pants, Polo, Shirt, Shoes, Shorts, Skirt, T-Shirt, Top, Undershirt.

In Mode B/C, `_orchestrate_stream()` still runs (producing Mode A's extracted slot), but its search results are **discarded** — the agentic orchestrator calls `run_search_tool()` independently. This means a Mode A-only guard would be insufficient.

## Goals / Non-Goals

**Goals:**
- Intercept unsupported categories before any search is performed for all three modes
- Return a multilingual refusal with 2–3 proactive suggestions from the supported catalog
- Zero additional LLM calls for the validation step
- Safety-net in `run_search_tool()` to prevent agentic LLMs from independently searching invalid categories

**Non-Goals:**
- Semantic reclassification of the user's request (not replacing their intent, just refusing politely)
- Dynamic discovery of supported categories from the DB at runtime (static list is sufficient)
- Changing the slot completeness or clarification gate logic

## Decisions

### Decision 1: Two-Layer Defense (Pre-flight + Safety Net)

**Chosen**: Layer the validation at two points:
1. **Pre-flight in `chat_stream()`** — after `_orchestrate_stream()` returns, and BEFORE branching to agentic — check `result.filters.get("category")` against `SUPPORTED_CATEGORIES`. If invalid, emit `clarification` SSE and return early.
2. **Safety net in `run_search_tool()`** — if `category` arg is not in the supported set, return `[{"__error__": "unsupported_category", "requested": category, "suggestions": [...]}]` so the agentic orchestrator receives a meaningful signal.

**Alternative A considered**: Validate only in `_resolve_search_query()` (Mode A path):
- ❌ Rejected — Mode B/C discard Mode A's search results entirely; the agentic orchestrator's own tool calls bypass this check.

**Alternative B considered**: Validate only in `run_search_tool()`:
- ❌ Rejected as sole guard — the agentic LLM might interpret an error dict and retry, wasting tokens. Pre-flight ensures we return a clean refusal to the user immediately.

**Alternative C considered**: Add catalog awareness to the intent prompt:
- ❌ Rejected — LLM-based validation is non-deterministic. A hardcoded check against 17 labels is perfectly reliable and costs nothing.

### Decision 2: Static Mapping + Fuzzy Fallback

**Chosen**: Maintain a `UNSUPPORTED_CATEGORY_SUGGESTIONS` dict of the most common unsupported items → alternatives. For anything not in the dict, use `rapidfuzz.process.extractOne()` against the 17 labels (similarity threshold ≥ 60).

```python
UNSUPPORTED_CATEGORY_SUGGESTIONS = {
    "bikini":    ["Body", "Top", "Shorts"],
    "swimsuit":  ["Body", "Shorts"],
    "swimwear":  ["Body", "Shorts", "Top"],
    "jeans":     ["Pants", "Shorts"],
    "denim":     ["Pants", "Shorts"],
    "coat":      ["Outwear", "Blazer"],
    "jacket":    ["Outwear", "Blazer", "Hoodie"],
    "cardigan":  ["Outwear", "Longsleeve"],
    "sweater":   ["Hoodie", "Longsleeve"],
    "suit":      ["Blazer", "Pants"],
    "sneakers":  ["Shoes"],
    "boots":     ["Shoes"],
    "heels":     ["Shoes"],
    "bra":       ["Body", "Undershirt"],
    "underwear": ["Undershirt", "Body"],
    "pyjamas":   ["Undershirt", "Longsleeve"],
    "lingerie":  ["Body", "Undershirt"],
    "vest":      ["Top", "Undershirt"],
    "crop top":  ["Top", "Blouse"],
    "tank top":  ["Top", "Undershirt"],
    "turtleneck":["Longsleeve", "Top"],
    "scarf":     ["Hat"],  # closest accessory
    "cap":       ["Hat"],
    "bag":       [],  # no close equivalent — empty means "no suggestions"
    "watch":     [],
}
```

**Alternative**: Embedding similarity against label vectors — overkill for 17 labels; `rapidfuzz` is pure-Python and has no latency overhead.

### Decision 3: `SUPPORTED_CATEGORIES` location

**Chosen**: Define in `agent/utils.py` (already contains shared utilities like `format_history_text`). Both `fashion_agent.py` and `tools.py` already import from `agent/utils.py`.

**Alternative**: New `agent/constants.py` — adds a file but no meaningful benefit for this scope.

### Decision 4: Refusal via existing `clarification` SSE event

**Chosen**: Reuse the `clarification` event channel — already handled by the frontend/client. The refusal text is formatted identically to `OUT_OF_SCOPE_RESPONSE` in `prompts.py`.

No new SSE event type needed.

## Risks / Trade-offs

- **Static map maintenance** → If new labels are ever added to the DB, `SUPPORTED_CATEGORIES` must be manually updated. *Mitigation*: Add a startup assertion that logs a warning if DB labels don't match the constant.
- **Fuzzy matching false positives** → `rapidfuzz` might suggest "Shirt" for "skirt" (already supported). *Mitigation*: Check the supported set before fuzzy — only fuzzy match if category is truly unsupported.
- **Agentic LLM ignoring error dict** → If GPT/Claude receives the error result from `run_search_tool()` and retries with a different query, it may find results anyway. *Mitigation*: The pre-flight guard in `chat_stream()` ensures the user already received a refusal before the agentic branch runs; any synthesis that follows would be low-quality but wouldn't show more products (products are empty at this point).
- **Multilingual category names** → A Vietnamese user might type "áo bikini" — the intent classifier extracts "Bikini" in English from the slot, so validation still works correctly.

## Migration Plan

1. Add `SUPPORTED_CATEGORIES`, suggestions dict, and `_find_category_suggestions()` to `agent/utils.py`
2. Add `UNSUPPORTED_CATEGORY_RESPONSE` multilingual strings to `agent/prompts.py`
3. Implement pre-flight guard in `chat_stream()` (Mode A + B/C coverage)
4. Implement guard in `_resolve_search_query()` for the non-streaming `chat()` path
5. Add safety-net in `run_search_tool()` in `agent/tools.py`
6. Add `rapidfuzz` to `pyproject.toml` dependencies
7. Rebuild Docker container: `docker compose up -d --build fashion-api`
8. Smoke test: send "find me a bikini" in all three modes (A/B/C)

**Rollback**: Revert the three modified files — no DB changes, no migration needed.

## Open Questions

- *(none — design is complete based on exploration; implementation can proceed)*

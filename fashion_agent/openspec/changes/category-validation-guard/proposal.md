## Why

When a user queries an unsupported clothing category (e.g., "bikini", "jeans", "sneakers"), the agent silently searches and returns semantically similar but irrelevant results — leading to a confusing UX and poor catalog quality perception. The system must detect unsupported categories early, refuse gracefully, and guide the user toward supported alternatives.

## What Changes

- **New**: `SUPPORTED_CATEGORIES` canonical constant listing all 17 DB labels (Blazer, Blouse, Body, Dress, Hat, Hoodie, Longsleeve, Outwear, Pants, Polo, Shirt, Shoes, Shorts, Skirt, T-Shirt, Top, Undershirt)
- **New**: `UNSUPPORTED_CATEGORY_SUGGESTIONS` static mapping from common unsupported items to 2–3 supported alternatives (e.g., `"bikini" → ["Body", "Top", "Shorts"]`)
- **New**: Category validation step in `_resolve_search_query()` (Mode A guard — deterministic, zero extra LLM calls)
- **New**: Pre-flight category check in `chat_stream()` before entering agentic branch (Mode B/C guard — uses already-extracted slot from Mode A intent classification)
- **New**: Safety-net validation in `run_search_tool()` — returns structured error result if `category` arg is not in supported set (prevents agentic LLMs from searching invalid categories independently)
- **New**: Multilingual refusal messages in `prompts.py` following the `OUT_OF_SCOPE_RESPONSE` pattern (EN, VI, ES)
- **New**: Fuzzy fallback using `rapidfuzz` to find closest valid label for unrecognized category names not in the static suggestion map

## Capabilities

### New Capabilities

- `category-validation`: Validates extracted clothing categories against the known DB label set, intercepts unsupported ones with a polite refusal and proactive suggestions for all three orchestration modes (A/B/C)

### Modified Capabilities

- *(none — existing search, slot completeness, and clarification logic are unchanged; this is purely additive)*

## Impact

**Files modified:**
- `fashion_agent/agent/fashion_agent.py` — validation in `_resolve_search_query()` + pre-flight check in `chat_stream()`
- `fashion_agent/agent/tools.py` — safety-net validation in `run_search_tool()`
- `fashion_agent/agent/prompts.py` — add `UNSUPPORTED_CATEGORY_RESPONSE` multilingual strings
- `fashion_agent/agent/utils.py` (or new `constants.py`) — `SUPPORTED_CATEGORIES`, `UNSUPPORTED_CATEGORY_SUGGESTIONS`, `_find_category_suggestions()`

**Dependencies added:**
- `rapidfuzz` (lightweight fuzzy matching; already a common Python dependency)

**No API changes** — refusal is returned via the existing `clarification` SSE event channel  
**No DB changes** — validation is purely in-memory against the hardcoded label set  
**No breaking changes** — all three orchestration modes remain backward-compatible

## ADDED Requirements

### Requirement: Supported category constant
The system SHALL maintain a hardcoded set of supported clothing categories (`SUPPORTED_CATEGORIES`) in `agent/utils.py` that exactly matches the 17 distinct `label` values in the `fashion_items` database table: Blazer, Blouse, Body, Dress, Hat, Hoodie, Longsleeve, Outwear, Pants, Polo, Shirt, Shoes, Shorts, Skirt, T-Shirt, Top, Undershirt.

#### Scenario: Valid category passes through
- **WHEN** the user queries a category that exists in `SUPPORTED_CATEGORIES` (e.g., "find me a dress")
- **THEN** the agent proceeds to search normally without triggering any refusal

#### Scenario: Invalid category is rejected
- **WHEN** the user queries a category NOT in `SUPPORTED_CATEGORIES` (e.g., "find me a bikini")
- **THEN** the agent MUST NOT perform any search and MUST return a refusal message

---

### Requirement: Multilingual refusal message with suggestions
The system SHALL respond to unsupported category queries with an `UNSUPPORTED_CATEGORY_RESPONSE` message that:
1. Names the requested category
2. Explains it is not available
3. Lists 2–3 alternative supported categories from the static suggestion map or fuzzy fallback
4. Is delivered in the detected language of the user query (EN, VI, or ES)

#### Scenario: English refusal with suggestions
- **WHEN** an English-speaking user requests "bikini"
- **THEN** the agent returns a message like: "Sorry, we don't carry Bikini in our catalog. You might enjoy: Body, Top, or Shorts."

#### Scenario: Vietnamese refusal with suggestions
- **WHEN** a Vietnamese user requests "bikini" or "áo bikini"
- **THEN** the agent returns an equivalent refusal message in Vietnamese with the same suggestions

#### Scenario: No suggestions available
- **WHEN** the unsupported category has no mapping (e.g., "watch", "bag") and fuzzy match score < 60
- **THEN** the agent returns a refusal without suggestions, inviting the user to browse available categories

---

### Requirement: Mode A pre-search validation (non-streaming)
The system SHALL validate the extracted `slot_category` in `_resolve_search_query()` before any hybrid search is performed. If the category is unsupported, the function SHALL set `clarification` on the result and return immediately.

#### Scenario: Mode A guard intercepts unsupported category
- **WHEN** `_resolve_search_query()` is called with `slot_category = "Bikini"`
- **THEN** the function returns an `OrchestrateResult` with `clarification` set to the refusal message and `products` as an empty list
- **AND** `hybrid_search()` is NEVER called

---

### Requirement: Mode B/C pre-flight validation (streaming)
The system SHALL check the extracted `slot_category` from `OrchestrateResult` in `chat_stream()` BEFORE entering the agentic orchestration branch. If the category is unsupported, `chat_stream()` SHALL emit a `clarification` SSE event and return early without invoking `orchestrate_with_gemini()` or `orchestrate_with_gpt()`.

#### Scenario: Mode B/C pre-flight guard intercepts unsupported category
- **WHEN** `chat_stream()` receives an `OrchestrateResult` with invalid `slot_category` and `orch_mode == "agentic"`
- **THEN** the function emits `event: clarification` with the refusal text
- **AND** `orchestrate_with_gemini()` / `orchestrate_with_gpt()` are NEVER called

#### Scenario: Mode B/C allows valid category through
- **WHEN** `chat_stream()` receives a valid `slot_category` (e.g., "Dress")
- **THEN** the function proceeds normally to the agentic orchestrator

---

### Requirement: run_search_tool safety-net validation
The system SHALL validate the `category` parameter in `run_search_tool()`. If the value is non-empty and not in `SUPPORTED_CATEGORIES`, the function SHALL return a list containing a single error dict `[{"__error__": "unsupported_category", "requested": <category>, "suggestions": [...]}]` instead of calling `hybrid_search()`.

#### Scenario: Tool-level guard returns error dict
- **WHEN** `run_search_tool(category="bikini")` is called by an agentic orchestrator
- **THEN** the function returns `[{"__error__": "unsupported_category", "requested": "bikini", "suggestions": ["Body", "Top", "Shorts"]}]`
- **AND** `hybrid_search()` is NEVER called

#### Scenario: Tool-level guard allows empty category
- **WHEN** `run_search_tool(category="")` is called
- **THEN** no category validation is performed and the search proceeds normally

---

### Requirement: Suggestion lookup with fuzzy fallback
The system SHALL provide category suggestions via a `_find_category_suggestions(category: str) -> list[str]` function in `agent/utils.py` that:
1. Normalizes `category` to lowercase
2. Checks `UNSUPPORTED_CATEGORY_SUGGESTIONS` static dict first
3. Falls back to `rapidfuzz.process.extractOne()` against `SUPPORTED_CATEGORIES` if not in the static dict
4. Returns an empty list if fuzzy score < 60
5. Returns at most 3 suggestions

#### Scenario: Static map lookup
- **WHEN** `_find_category_suggestions("jeans")` is called
- **THEN** returns `["Pants", "Shorts"]` from the static map

#### Scenario: Fuzzy fallback lookup
- **WHEN** `_find_category_suggestions("hoodie jacket")` is called (not in static map)
- **THEN** `rapidfuzz` finds "Hoodie" as the closest match with score ≥ 60
- **AND** returns `["Hoodie"]`

#### Scenario: No match found
- **WHEN** `_find_category_suggestions("watch")` is called and score < 60
- **THEN** returns `[]`

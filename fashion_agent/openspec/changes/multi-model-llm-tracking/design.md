## Context

The Fashion Agent is a FastAPI + Flutter thesis system. The backend uses a single `shared/llm.py` that wraps `google-generativeai` exclusively. Every synthesis call in `fashion_agent.py` calls `get_model()` which returns a `genai.GenerativeModel`. Token logging hardcodes `"gemini-2.5-flash"` as the model name. The Flutter registration screen collects name, birth year, and gender; the `user_sessions` table has no `preferred_model` column. The public leaderboard (`/api/ratings`) returns ratings joined against `user_sessions` but does NOT join `session_token_summary`, so model name never appears. `openai` and `anthropic` Python packages are not in `pyproject.toml`.

## Goals / Non-Goals

**Goals:**
- Introduce a provider-agnostic `LLMClient` abstraction supporting Gemini, GPT-4o, and Claude in one file
- Store `preferred_model` per session and route each chat request to the correct provider
- Fix hardcoded model name so token logs always reflect the actual provider
- Expose model name in the public leaderboard and Professor Dashboard
- Add a model picker to the Flutter registration screen
- Implement full behaviour tracking: fullscreen image zoom, cart removals, and position tracking on selection confirmation

**Non-Goals:**
- Load-balancing or failover between providers
- Fine-tuning or model versioning beyond the three fixed model IDs
- Streaming token-by-token display differences between providers (all use same SSE contract)
- Support for more than one model per session (single choice at registration)

## Decisions

### D1: Unified `LLMClient` protocol in `shared/llm.py`

**Decision**: Replace `get_model()` with a thin `LLMClient` protocol that each provider adapter implements.

```
class LLMClient(Protocol):
    model_name: str
    def generate(self, prompt: str) -> str: ...
    def stream(self, prompt: str) -> Generator[str, None, TokenUsage]: ...
```

Three concrete classes: `GeminiClient`, `OpenAIClient`, `AnthropicClient`. A factory `get_client(model_id: str) -> LLMClient` dispatches by prefix (`gemini-*`, `gpt-*`, `claude-*`).

**Why over alternatives:**
- *Subclass hierarchy*: rejected — providers have incompatible SDK shapes; duck typing is simpler
- *Strategy dict*: too rigid for streaming; method-based protocol allows per-provider logic
- *Keep Gemini-only + env switch*: doesn't support per-session model choice

### D2: Session-level model binding via `preferred_model` column

**Decision**: Add `preferred_model TEXT DEFAULT 'gemini-2.5-flash'` to `user_sessions`. At chat time, `_orchestrate_stream()` calls `get_session_model(session_id)` → `get_client(model_id)` and passes the client into synthesis functions.

**Why**: The session is the natural unit of model binding for thesis evaluation. Per-message model choice would complicate analysis. Default preserves backward compatibility with existing sessions.

### D3: Three hardcoded model IDs, user sees friendly names

**Supported IDs** (hardcoded in backend allowlist):
| Friendly Name | Model ID | Env Var |
|---|---|---|
| Gemini 2.5 Flash | `gemini-2.5-flash` | `GEMINI_API_KEY` |
| GPT-4o | `gpt-4o` | `GPT_API_KEY` |
| Claude 3.5 Sonnet | `claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` |

Registration sends the model ID string. Backend validates against allowlist; unknown models default to Gemini.

### D4: Position tracking on selection via `product_clicks` join

**Decision**: When `_handle_confirm()` saves items, for each `image_id` look up the most recent `product_clicks.position` for that `(session_id, image_id)`. Store in `selected_items.position`.

**Why over UI pass-through**: The click position is already persisted in `product_clicks` the moment the card is tapped (before confirm). No UI changes needed. The join is deterministic since click precedes confirm.

### D5: Cart removal as a separate `cart_removals` event log

**Decision**: New append-only `cart_removals(session_id, image_id, removed_at)` table. `DELETE /api/sessions/{id}/selections/{image_id}` hard-deletes from `selected_items` AND inserts into `cart_removals`.

**Why**: Separating removal events from the selections table preserves the full funnel history for analytics. A soft-delete flag in `selected_items` would complicate cart display queries.

### D6: Fullscreen zoom via Flutter `showDialog` overlay

**Decision**: On `_ProductCard.onTap`, after firing `logClick()`, push a `Dialog` with a black background and the product image in a `InteractiveViewer` (pinch-to-zoom + pan). Tap anywhere outside to dismiss.

**Why**: `showDialog` is the standard Flutter fullscreen pattern. Works on web without native navigation. `InteractiveViewer` is built-in, no extra package needed.

## Risks / Trade-offs

- **Anthropic SDK cold start** → Mitigation: lazy-import inside `AnthropicClient.__init__()` so missing key only fails at runtime for Claude sessions, not on server startup
- **OpenAI/Anthropic streaming format differs** → Mitigation: each client's `stream()` method normalises chunks to plain `str` tokens + final `TokenUsage`; `fashion_agent.py` only consumes the abstraction
- **`product_clicks` join miss** → If a user saves an item without clicking it (edge case), position defaults to 0. Acceptable for thesis data.
- **No ANTHROPIC_API_KEY yet** → Claude sessions will raise `RuntimeError`; mitigated by server-side validate-on-call (not validate-on-startup) and clear error message; user must add key to `.env`

## Migration Plan

1. Add `openai` and `anthropic` to `pyproject.toml` → rebuild Docker image
2. Add `ANTHROPIC_API_KEY` to `.env` (if Claude is enabled)
3. Run `init_memory_tables()` on startup (already called) — idempotent `ALTER TABLE IF NOT EXISTS` adds new columns/tables without data loss
4. Deploy updated Docker stack (`docker compose up --build -d`)
5. Existing sessions retain `preferred_model = NULL` → treated as `"gemini-2.5-flash"` by `get_session_model()`

## Open Questions

- Claude API key: user to provide `ANTHROPIC_API_KEY`; until then Claude option can be shown in UI but gracefully fallback to an error message on first chat turn
- Should the leaderboard model column be visible to all users (public) or only to the Professor Dashboard? **Decision: public leaderboard shows model name** (thesis transparency)

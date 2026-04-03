## Why

The Fashion Agent is locked to a single LLM provider (Gemini). For the thesis, we need to compare recommendation quality across Google Gemini, OpenAI GPT-4o, and Anthropic Claude — giving each test user agency to choose their model. Additionally, the leaderboard doesn't surface which model powered each session, and the system lacks full funnel tracking (image zoom on tap, cart removals, and image index on selection) needed to compute reranker precision.

## What Changes

- **Backend: Multi-provider LLM abstraction** — `shared/llm.py` refactored from Gemini-only `get_model()` to a unified `LLMClient` interface supporting Gemini, OpenAI (`gpt-4o`), and Anthropic (`claude-3-5-sonnet-20241022`)
- **Backend: Session model binding** — `user_sessions` table gains a `preferred_model` column; `create_session()` accepts and stores it; the agent reads it per-request and routes to the correct provider
- **Backend: Token logging fixed** — hardcoded `"gemini-2.5-flash"` model name in `fashion_agent.py` replaced with dynamically resolved name from the active client
- **Backend: Leaderboard join** — `/api/ratings` query adds a `LEFT JOIN session_token_summary` to return `model_name` and `total_tokens` per entry
- **Backend: Behaviour tracking (image index on selection)** — `selected_items` gains a `position` column; when confirm fires, the position from `product_clicks` is joined to record which rank the user ultimately saved
- **Backend: Cart removal tracking** — new `cart_removals` table; new `DELETE /api/sessions/{id}/selections/{image_id}` endpoint; `log_cart_removal()` function
- **Frontend: Model picker at registration** — `RegisterScreen` adds a segmented/radio control for model selection (Gemini / GPT-4o / Claude); value sent to `POST /api/sessions`
- **Frontend: Fullscreen image zoom** — `_ProductCard.onTap` opens a fullscreen image overlay/dialog before (or alongside) `logClick()`
- **Frontend: Leaderboard model column** — `_LeaderboardDialog` displays model badge alongside user name and rating
- **Frontend: Cart removal UI** — `_CartCard` adds a swipe-to-delete or ❌ button; calls new `removeCartItem()` in `ApiService`
- **Dependencies**: Add `openai` and `anthropic` Python packages to `pyproject.toml` and Docker image

## Capabilities

### New Capabilities

- `multi-model-llm`: Unified LLM client abstraction supporting Gemini, OpenAI, and Claude; session-level model binding; correct model name in token logs
- `user-model-selection`: Registration UI for model choice; `preferred_model` stored in session; passed through to agent at chat time
- `leaderboard-model-column`: `/api/ratings` returns `model_name` and `total_tokens`; Flutter leaderboard renders model badge
- `behaviour-image-zoom`: Fullscreen product image overlay on tap in `ProductCardList`
- `behaviour-cart-removal`: `cart_removals` DB table, DELETE endpoint, frontend remove button, and removal event tracking
- `behaviour-selection-position`: `selected_items.position` column records the 1-based rank of the confirmed item from the last search

### Modified Capabilities

- `session-creation`: `CreateSessionRequest` and `create_session()` gain `preferred_model` field — existing callers unaffected (default: `"gemini-2.5-flash"`)

## Impact

- `fashion_agent/shared/llm.py` — full rewrite (new abstraction layer)
- `fashion_agent/agent/fashion_agent.py` — inject model client from session; fix hardcoded model name in `log_token_usage` calls
- `fashion_agent/agent/memory.py` — schema migrations: `user_sessions.preferred_model`, `selected_items.position`, new `cart_removals` table, `log_cart_removal()` function
- `fashion_agent/api/main.py` — update `CreateSessionRequest`; update `/api/ratings`; add `DELETE /api/sessions/{id}/selections/{image_id}`
- `fashion_agent/pyproject.toml` + `Dockerfile` — add `openai`, `anthropic` dependencies
- `fashion_agent/.env` — add `ANTHROPIC_API_KEY`
- `clothie_web/lib/screens/register_screen.dart` — model picker widget
- `clothie_web/lib/widgets/product_card.dart` — fullscreen zoom dialog
- `clothie_web/lib/screens/cart_screen.dart` — remove button
- `clothie_web/lib/services/api_service.dart` — `removeCartItem()` method

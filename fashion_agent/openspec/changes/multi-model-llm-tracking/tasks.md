## 1. Python Backend — Dependencies & Configuration

- [x] 1.1 Add `openai` and `anthropic` to `fashion_agent/pyproject.toml` (or `requirements.txt`) and rebuild Docker image
- [x] 1.2 Add `ANTHROPIC_API_KEY=<your-key>` to `fashion_agent/.env`
- [x] 1.3 Verify `GPT_API_KEY` in `.env` is correctly named (currently saved as `GPT_API_KEY`; OpenAI SDK expects `OPENAI_API_KEY` — alias or rename)

## 2. Python Backend — Multi-Provider LLM Abstraction

- [x] 2.1 Rewrite `fashion_agent/shared/llm.py`: define `LLMClient` Protocol with `model_name`, `generate()`, `stream()` methods
- [x] 2.2 Implement `GeminiClient` class in `shared/llm.py` wrapping existing `google-generativeai` SDK logic
- [x] 2.3 Implement `OpenAIClient` class in `shared/llm.py` using `openai` SDK (`chat.completions.create`, streaming via `stream=True`)
- [x] 2.4 Implement `AnthropicClient` class in `shared/llm.py` using `anthropic` SDK (`messages.stream()`); lazy-import to avoid startup crash when key is missing
- [x] 2.5 Implement factory `get_client(model_id: str) -> LLMClient` dispatching by prefix; unknown prefix defaults to `GeminiClient`

## 3. Python Backend — Session Model Binding

- [x] 3.1 Add `preferred_model TEXT DEFAULT 'gemini-2.5-flash'` to `user_sessions` via `ALTER TABLE IF NOT EXISTS` in `init_memory_tables()` in `memory.py`
- [x] 3.2 Update `create_session()` in `memory.py` to accept `preferred_model: str = "gemini-2.5-flash"` and store it
- [x] 3.3 Add `get_session_model(session_id: str) -> str` helper in `memory.py` that reads `user_sessions.preferred_model`
- [x] 3.4 Update `CreateSessionRequest` in `api/main.py` to include `preferred_model: str = "gemini-2.5-flash"` with allowlist validation
- [x] 3.5 Pass `preferred_model` through `create_session_endpoint()` → `create_session()`

## 4. Python Backend — Wire LLM Client into Agent

- [x] 4.1 In `fashion_agent.py` `_orchestrate_stream()`: call `get_session_model(session_id)` then `get_client(model_id)` at the top; pass `client` into synthesis functions
- [x] 4.2 Update `_synthesize_response()` to accept `client: LLMClient` parameter and use `client.generate()` instead of `get_model().generate_content()`
- [x] 4.3 Update `_synthesize_response_stream()` to accept `client: LLMClient` and use `client.stream()`; adapt token usage extraction per client
- [x] 4.4 Replace hardcoded `"gemini-2.5-flash"` strings in `log_token_usage()` calls with `client.model_name`

## 5. Python Backend — Behaviour Tracking Schema

- [x] 5.1 Add `position INT NOT NULL DEFAULT 0` to `selected_items` via `ALTER TABLE IF NOT EXISTS` in `init_memory_tables()`
- [x] 5.2 Create `cart_removals` table (`id BIGSERIAL PRIMARY KEY, session_id TEXT, image_id VARCHAR, removed_at TIMESTAMPTZ`) in `init_memory_tables()`
- [x] 5.3 Add `log_cart_removal(session_id: str, image_id: str)` function to `memory.py` (insert into `cart_removals`, delete from `selected_items`)

## 6. Python Backend — Confirm & Removal Endpoints

- [x] 6.1 Update `_handle_confirm()` in `fashion_agent.py`: after determining items to save, look up `product_clicks.position` for each `(session_id, image_id)` and include `position` in the `items_to_save` dict
- [x] 6.2 Update `save_selected_items()` in `memory.py` to accept and insert `position` per item
- [x] 6.3 Add `DELETE /api/sessions/{session_id}/selections/{image_id}` endpoint in `api/main.py` calling `log_cart_removal()`
- [x] 6.4 Update `/api/ratings` query to `LEFT JOIN session_token_summary sts ON sts.session_id = r.session_id` and include `model_name`, `total_tokens` in returned entries

## 7. Flutter Frontend — Registration Model Picker

- [x] 7.1 Add `String _selectedModel = 'gemini-2.5-flash'` state variable to `_RegisterScreenState`
- [x] 7.2 Add a segmented button / radio group widget below the gender picker in `RegisterScreen` showing "Gemini", "GPT-4o", "Claude" choices
- [x] 7.3 Update `_startChat()` to pass `_selectedModel` to `_api.createSession()`
- [x] 7.4 Update `ApiService.createSession()` to include `preferred_model` in the POST body

## 8. Flutter Frontend — Fullscreen Image Zoom

- [x] 8.1 In `_ProductCard.onTap` (in `product_card.dart`): after `logClick()`, call `_showFullscreenImage(context, widget.product.imageUrl, widget.product.label)`
- [x] 8.2 Implement `_showFullscreenImage()` as a `showDialog` with black `barrierColor`, containing `InteractiveViewer` wrapping `Image.network`; tapping outside dismisses
- [x] 8.3 Verify both click tracking and zoom work on Web (test in browser)

## 9. Flutter Frontend — Cart Removal

- [x] 9.1 Add `removeCartItem(sessionId, imageId)` method to `ApiService` calling `DELETE /api/sessions/{id}/selections/{imageId}`
- [x] 9.2 Add remove button (IconButton with `Icons.delete_outline`) to `_CartCard` in `cart_screen.dart`
- [x] 9.3 On remove button tap: call `removeCartItem()`, then call `context.read<CartProvider>().reload()`
- [ ] 9.4 Verify cart badge count decrements correctly after removal

## 10. Flutter Frontend — Leaderboard Model Column

- [x] 10.1 Update `_LeaderboardDialog` in `register_screen.dart` to read `model_name` and `total_tokens` from each entry map
- [x] 10.2 Add a model badge chip (e.g., coloured `Chip`) next to user name showing short model label ("Gemini", "GPT-4o", "Claude", or "—")
- [x] 10.3 Optionally display `total_tokens` as a small subtitle under the user name

## 11. Verification

- [x] 11.1 Run `docker compose up --build -d` and confirm all containers start without errors
- [x] 11.2 Register a session with GPT-4o; chat; verify `llm_token_usage.model_name = "gpt-4o"` in DB
- [x] 11.3 Tap a product card; verify fullscreen zoom opens and click is logged in `product_clicks`
- [x] 11.4 Confirm a selection; verify `selected_items.position` is correctly populated
- [x] 11.5 Remove a cart item; verify row deleted from `selected_items` and inserted into `cart_removals`
- [x] 11.6 Open leaderboard after submitting a rating; verify model badge appears

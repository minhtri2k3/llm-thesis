## 1. Reinstate pre-search readiness gating

- [x] 1.1 Add a configurable confidence threshold and enforce confidence gating before executing `text_search` and `follow_up` queries.
- [x] 1.2 Apply slot completeness checks before search execution and return template-based clarification when required slots are missing.
- [x] 1.3 Ensure blocked requests do not execute retrieval and preserve merged session slot context for next-turn completion.

## 2. Add dedicated PATH 2 direct cart API contract

- [x] 2.1 Add request/response models and a `POST /api/sessions/{session_id}/selections` endpoint for direct selection insertion.
- [x] 2.2 Validate required payload fields (`image_id`, product metadata, `path_mode`) and reject invalid requests with explicit 4xx responses.
- [x] 2.3 Persist direct selections through existing `save_selected_items` path with `path_mode=path2` and idempotent duplicate handling.

## 3. Wire PATH 2 UI add-to-cart to direct insertion flow

- [x] 3.1 Add frontend API client method for direct selection insertion and expose success/error handling to chat/cart state managers.
- [x] 3.2 Route PATH 2 product-card add-to-cart actions to the direct endpoint instead of conversational numeric-select + confirm flow.
- [x] 3.3 Refresh cart state and show add confirmation feedback after successful direct PATH 2 insertion.

## 4. Validate behavior and path attribution

- [x] 4.1 Add backend tests for confidence/slot gating behavior (blocked search, clarification emitted, and pass-through when ready).
- [x] 4.2 Add backend tests for direct PATH 2 selection endpoint (success, validation failure, duplicate insertion semantics).
- [x] 4.3 Add/update frontend tests for PATH 2 add-to-cart UX and verify cart retrieval reflects `path_mode=path2`.

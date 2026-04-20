# Proposal: Clothie Agent UX v3

## Summary

A batch of targeted improvements across the Fashion Agent backend (`fashion_agent/`) and the
Clothie Flutter frontend (`clothie_web/`), addressing one critical bug and five UX improvements
identified through post-deployment testing and user feedback.

## Problems Being Solved

### 🐛 Bug 1 — Images always stuck loading (Critical)

When the backend emits the `products` SSE event, `image_path` is sent as the **full disk path**
(e.g., `/app/dataset_images/images_compressed/img.jpg`) rather than just the filename. The Flutter
client constructs `imageUrl` as `baseUrl + '/api/images/' + image_path`, producing a malformed URL
like `/api/images//app/dataset_images/images_compressed/img.jpg`. The image endpoint `GET
/api/images/{filename:path}` technically accepts paths, but the double-slash and leading `/`
cause it to 404, leaving every product image in a permanent loading state.

The fix is to apply `os.path.basename()` to each `image_path` in `chat_stream()` before building
the `product_dicts` list for the SSE payload — consistent with how `GET
/api/sessions/{id}/selections` already handles this on line 196 of `api/main.py`.

Additionally, there is a duplicate `except` block in `_synthesize_response_stream()` (lines
261–263 of `fashion_agent.py`) that is dead code and should be removed to prevent future
confusion.

### UX 1 — AI is too restrictive and not personalised

The slot completeness gate (`check_slot_completeness`) blocks searches if `category` is missing
even for rich queries like "something casual for a beach holiday". Users repeatedly hit
clarification turns that feel unnecessary. The agent should search first and clarify only when the
user's intent is genuinely ambiguous (confidence < 0.5), not whenever a structured slot is absent.

Additionally, the user's accumulated `get_preferences()` data (preferred colours, categories) is
used in the synthesis prompt but never injected into the **search query itself**, meaning the
vector search ignores this personalisation signal entirely.

### UX 2 — AI does not anticipate what the user wants next

The synthesis prompt instructs Gemini to describe found items but does not ask it to proactively
suggest complementary pieces or next steps. Users feel the conversation is reactive rather than
guiding. For vague queries, `use_query_expansion=False` means semantically related items are
missed.

### UX 3 — Thinking state has no visual skeleton (poor perceived performance)

While the agent is classifying intent and searching (typically 2–4 seconds), the Flutter UI shows
only a faint spinner. Users perceive the app as frozen. A shimmer skeleton that mimics the product
card grid would communicate that something is happening and improve perceived performance
significantly.

### UX 4 — No way to write a multi-line message (Shift+Enter)

The chat input field sends on every Enter key press, making it impossible to compose structured
messages (e.g., "I'm looking for:\n- a casual shirt\n- in navy blue") without sending
prematurely. Every modern messaging product supports Shift+Enter for newlines.

### UX 5 — Rating system is overwhelming and misses key research questions

The current 1–10 scale with a single free-text field overwhelms users (too many options, no
guidance) and fails to capture the two distinct dimensions the thesis needs to measure:
**suggestion relevance** and **conversational quality**. A 1–5 scale with three targeted questions
is both less intimidating and more analytically useful.

## Goals

| # | Goal | Constraint |
|---|------|------------|
| Bug | Fix image loading by stripping basename in SSE payload | No DB change, no new endpoints |
| Bug | Remove dead `except` block in `_synthesize_response_stream` | Pure cleanup |
| UX 1 | Search first, clarify only on genuine ambiguity | Keep MAX_CLARIFICATION_TURNS as safety cap |
| UX 1 | Inject top preference into search query expansion | Use existing `get_preferences()` |
| UX 2 | Enable `query_expansion=True` for vague / follow-up intents | Already exists in `hybrid_search` |
| UX 2 | Update synthesis prompt to be proactive and suggest next steps | Prompt-only change |
| UX 3 | Add shimmer skeleton grid while `status == thinking` | Use `shimmer` package in Flutter |
| UX 4 | Shift+Enter inserts newline, plain Enter sends | Flutter Web `RawKeyboardListener` |
| UX 5 | Replace 1–10 single rating with 3 × 1–5 targeted questions | DB migration + Pydantic + Flutter |

## Non-Goals

- Changing the Qdrant index schema or product dataset.
- Adding new SSE event types (shimmer is purely client-side).
- Changing the registration, splash, or cart screens beyond the rating change.
- Modifying the agentic orchestration (Mode B/C) logic.

## Scope

### Backend (`fashion_agent/`)

- `agent/fashion_agent.py`
  - Strip `os.path.basename()` from `image_path` in `chat_stream()` product SSE payload.
  - Remove duplicate `except` block in `_synthesize_response_stream()`.
  - In `_resolve_search_query()`: remove completeness gate for `text_search`; only raise
    clarification when intent `confidence < 0.5` AND no query can be formed.
  - In `_route_and_execute()`: inject top-1 preferred colour/category into `search_query` when
    present in preferences.
  - In `_route_and_execute()`: pass `use_query_expansion=True` for `follow_up` intent.
  - Update `STREAM_SYNTHESIS_PROMPT` call: pass `proactive=True` hint.

- `agent/prompts.py`
  - Extend `STREAM_SYNTHESIS_PROMPT` to include a proactive suggestion paragraph.

- `api/main.py`
  - Update `RatingRequest` model: add `rating_suggestions: int` and `rating_conversation: int`
    fields (1–5 each); rename `rating` → `rating_overall` (still 1–5).
  - Update `submit_rating_endpoint` INSERT to include the new columns.

- `agent/memory.py`
  - Add `init_memory_tables()` DDL for new columns on `user_ratings`:
    `rating_overall INT CHECK (1-5)`, `rating_suggestions INT`, `rating_conversation INT`.

### Frontend (`clothie_web/`)

- `lib/screens/chat_screen.dart` / `lib/widgets/chat_bubble.dart`
  - Add `ShimmerProductGrid` widget shown when `aiMsg.status == MessageStatus.thinking`.

- `lib/widgets/chat_input.dart` (or equivalent)
  - Add `RawKeyboardListener` / `CallbackShortcuts`: Shift+Enter → insert `\n`; plain Enter →
    send.

- `lib/screens/rating_screen.dart` + `RatingDialog` widget
  - Replace single 1–10 `StarRating` with three 1–5 `StarRating` widgets.
  - Labels: "Overall experience", "Were the suggestions right for you?", "How did the
    conversation feel?".
  - Update `_submit()` to send all three values.

- `lib/services/api_service.dart`
  - Update `submitRating()` to pass `rating_overall`, `rating_suggestions`,
    `rating_conversation`.

## Architecture Decisions

**Basename stripping in Python (not Flutter)**: The backend owns the absolute path; the frontend
should receive a clean filename. Fixing it client-side would require heuristics; fixing it
server-side is one line and future-proof.

**Slot gate relaxation (search-first)**: Instead of requiring all slots before searching, the
agent now applies preferences as soft hints to the query string and searches immediately. If the
search returns 0 results, it asks for clarification. This matches how Google and modern search UX
works — show results first, refine later.

**Shimmer is client-only**: No new SSE events needed. The existing `thinking_start` event already
triggers `MessageStatus.thinking` in Flutter; the shimmer widget just replaces the spinner
displayed during that state.

**DB migration for ratings is additive**: New `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` DDL
added to `init_memory_tables()`. Old rows get `NULL` for the new columns (acceptable for
historic data). The existing `rating` column is kept as-is (historic data) but the new endpoint
writes to `rating_overall` instead. The 1–5 scale is enforced by a new `CHECK` constraint.

## Success Criteria

- [ ] All product images load correctly after the first search.
- [ ] "I want something casual for the beach" triggers a search immediately without clarification.
- [ ] Users with a colour preference get results that reflect it without explicitly naming the colour.
- [ ] Synthesis reply ends with a proactive "you might also try..." suggestion.
- [ ] A shimmer product skeleton is visible for the 2–4 seconds while the agent thinks.
- [ ] Shift+Enter in the chat input inserts a newline; Enter alone sends.
- [ ] The rating screen shows three 5-star widgets labelled clearly.
- [ ] New rating submissions are stored in all three columns.
- [ ] `docker compose up` starts the full stack without errors.

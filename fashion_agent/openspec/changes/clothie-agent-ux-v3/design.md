# Design: Clothie Agent UX v3

## Overview

Six changes across two codebases. All changes are additive or surgical — no new tables (only new
columns), no new SSE event types, no new API endpoints (only request model expansion).

---

## Change A — Fix: Images always loading (Critical Bug)

### Root Cause

In `chat_stream()` (`fashion_agent.py`, ~line 1225), the product SSE payload is built from
`NodeWithScore` objects whose `.image_path` is an **absolute disk path** such as:

```
/app/dataset_images/images_compressed/img_00001234.jpg
```

Flutter's `Product.fromJson` reads this as the image filename component, then builds:

```
http://host/api/images//app/dataset_images/images_compressed/img_00001234.jpg
```

The FastAPI endpoint `GET /api/images/{filename:path}` receives `filename =
"/app/dataset_images/images_compressed/img_00001234.jpg"` which starts with `/` and fails the
`DATASET_IMAGES_DIR / filename` resolution, producing a 404.

### Fix (exact diff)

In `fashion_agent.py`, `chat_stream()`, the product dict construction (currently ~lines 1225–1235):

```python
# BEFORE
product_dicts = [
    {
        "image_id": p.image_id,
        "image_path": p.image_path,           # ← full absolute path
        "label": p.label,
        "color": p.color,
        "caption": p.caption,
        "score": round(p.score, 4),
    }
    for p in result.products
]
```

```python
# AFTER
import os as _os  # already imported at top of file as `os`
product_dicts = [
    {
        "image_id": p.image_id,
        "image_path": os.path.basename(p.image_path),  # ← filename only
        "label": p.label,
        "color": p.color,
        "caption": p.caption,
        "score": round(p.score, 4),
    }
    for p in result.products
]
```

`os` is already imported at the top of `fashion_agent.py` (line 18). No additional import needed.

### Fix — Dead code removal

Remove the unreachable second `except` block in `_synthesize_response_stream()` (lines 261–263):

```python
# REMOVE these 3 lines (dead code — second except on same try):
    except Exception as exc:
        logger.warning("Streaming synthesis failed: %s", exc)
        yield ResponseToken(fallback_text_response(products))
```

---

## Change B — UX 1: Search-First, Personal-Aware AI

### Current behaviour (problem)

`_resolve_search_query()` calls `check_slot_completeness()` for every `text_search` intent. If
`category` slot is absent, it emits a clarification question regardless of how rich the user
query is. This fires on queries like "something for a beach holiday" where the intent is clear.

### Why a word-count pre-gate is wrong

A naïve fix of "only clarify if the query is < 3 words" creates a different loop:

```
User: "casual beach look"  (3 words — gate passes, search runs)
     → 0 results found
     → synthesis: "I couldn't find that"
     → user: "something beach casual"  (3 words — gate passes again)
     → 0 results again → no clarification → loop forever ✗
```

The correct fix is a **post-search gate**: always attempt the search; only ask for clarification
when the search returns **zero results**. The `MAX_CLARIFICATION_TURNS` counter prevents infinite
looping.

### Design — post-search zero-results gate

**Step 1: Remove the pre-search slot completeness gate entirely**

In `_resolve_search_query()`, the `text_search` branch currently has:

```python
is_complete, missing = check_slot_completeness(accumulated)
if not is_complete:
    clarify_count = _count_clarification_turns(history)
    if clarify_count < MAX_CLARIFICATION_TURNS:
        question = build_template_question(...)
        return "", question     # ← blocks search before it runs

search_query = compose_refined_query_from_slots(accumulated)
if not search_query.strip():
    search_query = intent_result.refined_query or ""
return search_query, ""
```

Replace the entire `text_search` branch with:

```python
if intent == "text_search":
    new_slots = intent_result.extracted_slots
    accumulated = _session_accumulated_slots.get(session_id, ExtractedSlots())

    if should_reset_slots(accumulated, new_slots):
        accumulated = ExtractedSlots()

    accumulated = merge_slots(accumulated, new_slots)
    _session_accumulated_slots[session_id] = accumulated

    # Category validation guard (unchanged)
    slot_category = accumulated.category
    if slot_category and slot_category not in SUPPORTED_CATEGORIES:
        lang = detect_language(query)
        suggestions = _find_category_suggestions(slot_category)
        refusal = build_unsupported_category_message(slot_category, suggestions, lang)
        return "", refusal

    # Build the best search query we can from slots + raw query
    search_query = compose_refined_query_from_slots(accumulated)
    if not search_query.strip():
        search_query = intent_result.refined_query or query

    # Always return the query — zero-results clarification happens AFTER the search
    return search_query, "", accumulated
```

The category validation guard is kept because category errors need to be caught before the search
(the search would return nonsense, not zero results). All other slot gates are removed.

**Step 2: Add post-search zero-results clarification gate in `_orchestrate_stream()`**

The `_orchestrate_stream()` function currently proceeds straight to `OrchestrateResult` after the
search. Add a zero-results check between `search_done` and `done`:

```python
    # Step 5: Route & execute search (0 LLM)
    yield ThinkingEvent("search", f"Searching: '{search_query[:50]}'...")
    products, reasoning = _route_and_execute(
        intent=intent,
        search_query=search_query,
        session_id=session_id,
        filters=intent_result.filters,
        preferences=preferences,            # ← also added here (see Step 3)
    )
    yield ThinkingEvent(
        "search_done",
        f"Found {len(products)} products...",
    )

    # ── NEW: Post-search zero-results clarification gate ─────────────────────
    if not products and intent in ("text_search", "follow_up"):
        clarify_count = _count_clarification_turns(history)
        if clarify_count < MAX_CLARIFICATION_TURNS:
            question = build_template_question(
                missing_slots=["category"], slots=accumulated_slots, query=query,
            )
            add_message(session_id, "assistant", question)
            yield ThinkingEvent(
                "done",
                f"No results — requesting clarification "
                f"(turn {clarify_count + 1}/{MAX_CLARIFICATION_TURNS}) — "
                f"{time.time() - start_time:.1f}s"
            )
            yield OrchestrateResult(
                intent="clarification",
                session_id=session_id,
                clarification=question,
                reasoning="Zero results — asking for more detail.",
                history=history,
                filters=intent_result.filters,
            )
            return
        # Max clarification turns reached — fall through and let synthesis
        # handle the zero-result state naturally ("I couldn't find...")
    # ── End post-search gate ─────────────────────────────────────────────────
```

**Why this eliminates the loop:**

| Scenario | Old gate | Word-count gate | Post-search gate (new) |
|----------|----------|-----------------|------------------------|
| Rich query → good results | ❌ Blocks, asks | ✅ Searches | ✅ Searches |
| Rich query → 0 results | ❌ Blocks anyway | ❌ Loops silently | ✅ Asks once, bounded |
| Vague 1-word query → 0 results | ❌ Blocks, asks | ❌ Loops if > 3 words | ✅ Asks, bounded |
| After MAX turns, still 0 results | ❌ Loops forever | ❌ Loops forever | ✅ Synthesis handles gracefully |

**Step 3: Inject top preference colour/category into search query**

In `_route_and_execute()`, add an optional `preferences` parameter and prepend the user's top
preferred colour/category to the search query as soft hints:

```python
def _route_and_execute(
    intent: str,
    search_query: str,
    session_id: str,
    filters: Optional[dict] = None,
    preferences: Optional[dict] = None,   # ← NEW parameter
) -> tuple[list[NodeWithScore], str]:

    # Soft preference injection — happens before any branch
    if preferences:
        pref_hints: list[str] = []
        top_color = (preferences.get("preferred_colors") or [None])[0]
        top_cat   = (preferences.get("preferred_categories") or [None])[0]
        # Only inject if not already present in the query
        if top_color and top_color.lower() not in search_query.lower():
            pref_hints.append(top_color)
        if top_cat and top_cat.lower() not in search_query.lower():
            pref_hints.append(top_cat)
        if pref_hints:
            search_query = search_query + " " + " ".join(pref_hints)
```

The call site in `_orchestrate_stream()` at Step 5 must pass `preferences`:

```python
products, reasoning = _route_and_execute(
    intent=intent,
    search_query=search_query,
    session_id=session_id,
    filters=intent_result.filters,
    preferences=preferences,          # ← NEW (preferences already loaded at Step 4)
)
```

Note: `preferences` is already loaded at Step 4 via `preferences = get_preferences(session_id)`
in `_orchestrate_stream()`, so no extra DB call is needed.

**Important: the slot accumulator (`accumulated`) reference in the post-search gate**

The `accumulated` variable is local to `_resolve_search_query()`, not accessible in
`_orchestrate_stream()`. To make it available to the post-search gate, `_resolve_search_query()`
must also return it:

```python
# Change _resolve_search_query() return type:
def _resolve_search_query(...) -> tuple[str, str, ExtractedSlots]:
    """Returns (search_query, clarification_message, accumulated_slots)."""
    ...
    return search_query, "", accumulated   # always return 3 values

# Update the call site in _orchestrate_stream():
search_query, clarification, accumulated_slots = _resolve_search_query(
    intent, intent_result, session_id, history, query,
)
```

Then in the post-search gate, use `accumulated_slots` instead of `accumulated`.

For non-`text_search` intents, `_resolve_search_query()` currently returns tuples of 2; update
all return sites to return a default `ExtractedSlots()` as the third element.

---

## Change C — UX 2: Proactive AI

### Query expansion for follow-up / vague intents

In `_route_and_execute()`, change the `follow_up` branch to use query expansion:

```python
# BEFORE
if intent in ("text_search", "follow_up"):
    products = hybrid_search(
        search_query,
        top_k=6,
        use_query_expansion=False,
        filters=filters,
    )

# AFTER
expansion = (intent == "follow_up")   # expansive for follow-ups
products = hybrid_search(
    search_query,
    top_k=6,
    use_query_expansion=expansion,
    filters=filters,
)
```

### Synthesis prompt update (`prompts.py`)

The `STREAM_SYNTHESIS_PROMPT` constant needs one additional paragraph at the end:

```python
# Add to the end of STREAM_SYNTHESIS_PROMPT (just before the closing triple-quote):
"""
After presenting the products, add a short "You might also like" suggestion (1–2 sentences)
that anticipates the user's next step. For example: if they searched for a shirt, suggest
what trousers or accessories would pair well. Keep it natural and conversational.
Do NOT add this section if no products were found.
"""
```

---

## Change D — UX 3: Shimmer Skeleton While Thinking

### Flutter widget

Add `ShimmerProductGrid` widget in `lib/widgets/shimmer_product_grid.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

class ShimmerProductGrid extends StatelessWidget {
  const ShimmerProductGrid({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final base  = isDark ? const Color(0xFF2A2A2A) : const Color(0xFFE0E0E0);
    final highlight = isDark ? const Color(0xFF3A3A3A) : const Color(0xFFF5F5F5);

    return Shimmer.fromColors(
      baseColor: base,
      highlightColor: highlight,
      child: GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
          childAspectRatio: 0.72,
        ),
        itemCount: 6,
        itemBuilder: (_, __) => Container(
          decoration: BoxDecoration(
            color: base,
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
    );
  }
}
```

**pubspec.yaml**: Add `shimmer: ^3.0.0` to `dependencies` if not already present.

### Integration in `chat_bubble.dart`

In the widget that renders product cards (currently shown when `aiMsg.products.isNotEmpty`),
add a branch for the thinking state:

```dart
// In the bubble's content builder, BEFORE the product grid:
if (message.status == MessageStatus.thinking && message.products.isEmpty)
  const ShimmerProductGrid(),

// Thinking steps text (already rendered below shimmer via thinkingSteps list)
```

The condition `message.products.isEmpty` ensures the shimmer disappears the moment real cards arrive.

---

## Change E — UX 4: Shift+Enter for New Line

### Location

The chat input field lives in `lib/screens/chat_screen.dart` or a dedicated
`lib/widgets/chat_input.dart` widget. The relevant widget wraps a `TextField` with
`textInputAction: TextInputAction.send` and `onSubmitted`.

### Implementation

Replace the `TextField` with a `CallbackShortcuts`-wrapped `TextField`:

```dart
// Remove: textInputAction: TextInputAction.send

// Add above TextField:
CallbackShortcuts(
  bindings: {
    const SingleActivator(LogicalKeyboardKey.enter, shift: true): () {
      final controller = _inputController;
      final text = controller.text;
      final sel  = controller.selection;
      final newText = text.replaceRange(sel.start, sel.end, '\n');
      controller.value = TextEditingValue(
        text: newText,
        selection: TextSelection.collapsed(offset: sel.start + 1),
      );
    },
  },
  child: TextField(
    controller: _inputController,
    maxLines: null,                       // allow multi-line
    keyboardType: TextInputType.multiline,
    textInputAction: TextInputAction.newline,  // mobile behaviour
    onSubmitted: null,                    // remove; use button instead
    // ... rest of decoration
  ),
),
```

The send action is moved to the `IconButton` / `ElevatedButton` that already exists in the input
row — it calls `_sendMessage(_inputController.text)`. This is the correct pattern for multi-line
chat inputs on Flutter Web.

**Note for mobile**: On mobile, the keyboard's action button (configured as `newline`) inserts a
newline. Sending is exclusively done via the send button. This matches WhatsApp/Telegram behaviour.

---

## Change F — UX 5: Rating System 1–5, Three Questions

### Database migration (additive only)

Add to `init_memory_tables()` DDL in `memory.py`, after the existing `user_ratings` table
creation:

```sql
-- Thesis evaluation v2: 1-5 scale, three targeted questions
ALTER TABLE user_ratings
    ADD COLUMN IF NOT EXISTS rating_overall INT CHECK (rating_overall BETWEEN 1 AND 5);
ALTER TABLE user_ratings
    ADD COLUMN IF NOT EXISTS rating_suggestions INT CHECK (rating_suggestions BETWEEN 1 AND 5);
ALTER TABLE user_ratings
    ADD COLUMN IF NOT EXISTS rating_conversation INT CHECK (rating_conversation BETWEEN 1 AND 5);
```

The existing `rating` column (1–10) is retained for backwards compatibility with historic data.
New submissions write to the three new columns AND set `rating = rating_overall * 2`
(approximate mapping to old scale) for analytics continuity.

### Backend API (`api/main.py`)

Update `RatingRequest` model:

```python
class RatingRequest(BaseModel):
    session_id: str
    rating_overall: int       # 1–5: overall experience
    rating_suggestions: int   # 1–5: were suggestions right?
    rating_conversation: int  # 1–5: how natural the conversation felt
    feedback: str = ""        # optional free text
```

Update `submit_rating_endpoint` validation and INSERT:

```python
@app.post("/api/rating", response_model=RatingResponse)
async def submit_rating_endpoint(req: RatingRequest):
    for field, val in [
        ("rating_overall", req.rating_overall),
        ("rating_suggestions", req.rating_suggestions),
        ("rating_conversation", req.rating_conversation),
    ]:
        if not (1 <= val <= 5):
            raise HTTPException(
                status_code=400,
                detail=f"{field} must be between 1 and 5",
            )
    # ... existing db connect ...
    cur.execute(
        """
        INSERT INTO user_ratings
            (session_id, user_name, rating,
             rating_overall, rating_suggestions, rating_conversation, feedback)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        (
            req.session_id,
            user_name,
            req.rating_overall * 2,       # backward-compat mapping
            req.rating_overall,
            req.rating_suggestions,
            req.rating_conversation,
            req.feedback,
        ),
    )
```

### Flutter — `lib/services/api_service.dart`

Update `submitRating()`:

```dart
Future<void> submitRating({
  required String sessionId,
  required int ratingOverall,
  required int ratingSuggestions,
  required int ratingConversation,
  String feedback = '',
}) async {
  await _dio.post('/api/rating', data: {
    'session_id': sessionId,
    'rating_overall': ratingOverall,
    'rating_suggestions': ratingSuggestions,
    'rating_conversation': ratingConversation,
    'feedback': feedback,
  });
}
```

### Flutter — `lib/screens/rating_screen.dart` state changes

```dart
// Replace single _rating with three fields:
int _ratingOverall = 0;
int _ratingSuggestions = 0;
int _ratingConversation = 0;

// Replace validation:
if (_ratingOverall == 0 || _ratingSuggestions == 0 || _ratingConversation == 0) {
  setState(() => _error = 'Please rate all three questions.');
  return;
}

// Replace API call:
await _api.submitRating(
  sessionId: widget.sessionId,
  ratingOverall: _ratingOverall,
  ratingSuggestions: _ratingSuggestions,
  ratingConversation: _ratingConversation,
  feedback: _feedbackController.text.trim(),
);
```

### Flutter — Rating UI structure (both `RatingScreen` and `RatingDialog`)

Replace the single `StarRating` block with three labelled 1–5 star widgets:

```dart
// Question 1 — Overall
_RatingQuestion(
  id: 'overall',
  label: 'Overall experience',
  value: _ratingOverall,
  onChanged: (v) => setState(() => _ratingOverall = v),
  maxStars: 5,
),
const SizedBox(height: 20),

// Question 2 — Suggestion relevance
_RatingQuestion(
  id: 'suggestions',
  label: 'Were the suggestions right for you?',
  value: _ratingSuggestions,
  onChanged: (v) => setState(() => _ratingSuggestions = v),
  maxStars: 5,
),
const SizedBox(height: 20),

// Question 3 — Conversational quality
_RatingQuestion(
  id: 'conversation',
  label: 'How natural did the conversation feel?',
  value: _ratingConversation,
  onChanged: (v) => setState(() => _ratingConversation = v),
  maxStars: 5,
),
```

The existing `StarRating` widget already accepts `value` and `onChanged`; it may need a `maxStars`
parameter added if it is hardcoded to 10. Check `lib/widgets/star_rating.dart` and add
`final int maxStars;` with `maxStars = 10` as default to preserve backward compatibility.

---

## Risk & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `os.path.basename()` strips subdirectory structure needed by image endpoint | High | The image endpoint already constructs `DATASET_IMAGES_DIR / "images_compressed" / filename` — it only needs the leaf filename. Verified on line 695 of `api/main.py`. |
| Search-first without clarification can produce poor results | Medium | The 3-word length guard catches truly empty queries. If 0 results returned, synthesis will produce a helpful "nothing found" message naturally. |
| Preference injection over-constrains the search | Medium | Preferences are appended as soft hints, not as hard filters. Hybrid search's BM25+vector fusion handles extra tokens gracefully. |
| Shimmer `shimmer` package not in pubspec.yaml | Low | Check `pubspec.yaml`; if absent, add `shimmer: ^3.0.0` and run `flutter pub get`. |
| `StarRating` widget hardcoded to 10 stars | Medium | Add `maxStars` param with default 10. All existing usages continue to work. |
| Old `rating` column (1–10) receives `rating_overall * 2` which maps 5→10 perfectly but 4→8, 3→6 etc. | Low | For thesis analytics, we query `rating_overall` directly; the old `rating` column is only kept for the existing leaderboard query until it can be updated. |
| `RatingRequest` breaking change — old clients send `rating: int` | Medium | Old `rating` field is removed from the model. Since Clothie Web is deployed as a single SPA alongside this backend, both are updated together in the same Docker build. |
| `CallbackShortcuts` on Flutter Web requires keyboard focus | Low | The `TextField` gains focus on tap. Shift+Enter is only meaningful on desktop/web; mobile keyboard always inserts newline on action key. |

# Tasks: Clothie Agent UX v3

Each task is a focused unit of work. Complete them in order — tasks within a group can be done in
parallel but the group itself must complete before the next group starts.

---

## Group 1 — Critical Bug Fix (Backend)

### Task 1.1 — Fix image_path in SSE product payload

**File**: `fashion_agent/agent/fashion_agent.py`

**What**: Strip `os.path.basename()` from `image_path` before emitting the `products` SSE event
so Flutter receives just the filename (e.g., `img_00001234.jpg`) not the absolute path.

**Where**: `chat_stream()` function, the `product_dicts` list comprehension (~line 1225).

**Change**:
```python
# BEFORE
"image_path": p.image_path,

# AFTER
"image_path": os.path.basename(p.image_path),
```

**Test**: Start the backend locally. Send a chat message. Open browser DevTools → Network → find
the SSE stream. Verify the `products` event data contains `"image_path": "img_00001234.jpg"` (no
leading `/` or directory parts). Then verify the image loads in the Flutter app.

---

### Task 1.2 — Remove dead except block

**File**: `fashion_agent/agent/fashion_agent.py`

**What**: Delete the duplicate (unreachable) second `except` block in
`_synthesize_response_stream()`.

**Where**: Lines 261–263 (approximately):
```python
    except Exception as exc:
        logger.warning("Streaming synthesis failed: %s", exc)
        yield ResponseToken(fallback_text_response(products))
```

**Change**: Delete those 3 lines entirely. The first `except Exception as e:` above them is the
correct handler.

**Test**: Run the existing synthesis path and confirm no `SyntaxError` or `IndentationError`.

---

## Group 2 — Search-First, Personalised AI (Backend)

### Task 2.1 — Update `_resolve_search_query()`: remove pre-search slot gate + fix return type

**File**: `fashion_agent/agent/fashion_agent.py`

**What**: Remove the `check_slot_completeness()` pre-search gate from the `text_search` branch.
Search always proceeds. Also change the function's return type from `tuple[str, str]` to
`tuple[str, str, ExtractedSlots]` so the caller can access accumulated slots for the
post-search clarification gate (Task 2.2).

**Why this matters**: Without this change, the agent was blocking searches before they even ran
when a category slot was missing. With this change, the agent always attempts a search. If it
finds results — great, no clarification needed. If it finds nothing — Task 2.2 then asks for
clarification exactly once (bounded by `MAX_CLARIFICATION_TURNS`).

**Where**: `_resolve_search_query()` function signature and `text_search` branch.

**Change 1** — Update function signature docstring:
```python
def _resolve_search_query(
    intent: str,
    intent_result: ClassifiedIntent,
    session_id: str,
    history: list[Message],
    query: str = "",
) -> tuple[str, str, ExtractedSlots]:  # ← CHANGED from tuple[str, str]
    """Resolve the search query.

    Returns:
        (search_query, clarification_message, accumulated_slots)
        ``clarification_message`` is non-empty when the caller should
        return early with a clarification question.
        ``accumulated_slots`` is the merged slot state (may be default
        ExtractedSlots() for non-text_search intents).
    """
```

**Change 2** — Replace the entire `text_search` branch:
```python
    if intent == "text_search":
        new_slots = intent_result.extracted_slots
        accumulated = _session_accumulated_slots.get(session_id, ExtractedSlots())

        if should_reset_slots(accumulated, new_slots):
            accumulated = ExtractedSlots()

        accumulated = merge_slots(accumulated, new_slots)
        _session_accumulated_slots[session_id] = accumulated

        # Category validation guard (unchanged — must stay pre-search)
        slot_category = accumulated.category
        if slot_category and slot_category not in SUPPORTED_CATEGORIES:
            lang = detect_language(query)
            suggestions = _find_category_suggestions(slot_category)
            refusal = build_unsupported_category_message(slot_category, suggestions, lang)
            return "", refusal, accumulated

        # Build the best search query we can — never block on missing slots
        search_query = compose_refined_query_from_slots(accumulated)
        if not search_query.strip():
            search_query = intent_result.refined_query or query

        # Always proceed to search — zero-results clarification happens AFTER
        return search_query, "", accumulated
```

**Change 3** — Update the `follow_up` branch (near end of function) to return 3 values:
```python
    if intent == "follow_up":
        # ... existing slot merge code ...
        slot_query = compose_refined_query_from_slots(accumulated)
        search_query = slot_query if slot_query.strip() else (intent_result.refined_query or "")
        return search_query, "", accumulated    # ← add accumulated
```

**Change 4** — Update all other `return` statements in the function to return 3 values:
```python
    # outfit_request, unclear, etc. (near end of function):
    if intent_result.confidence < 0.6 or intent == "unclear":
        clarification = check_clarification(...)
        if clarification.needs_clarification:
            return "", clarification.question, ExtractedSlots()  # ← add default

    return intent_result.refined_query or "", "", ExtractedSlots()  # ← add default
```

**Change 5** — Update the call site in `_orchestrate_stream()` (Step 3):
```python
# BEFORE
search_query, clarification = _resolve_search_query(
    intent, intent_result, session_id, history, query,
)

# AFTER
search_query, clarification, accumulated_slots = _resolve_search_query(
    intent, intent_result, session_id, history, query,
)
```

**Test**: Send "I want something casual for a beach holiday". Confirm:
- No clarification question appears.
- The backend log shows a search was attempted.
- Products are returned (or if 0 results, a clarification question from Task 2.2 fires).

---

### Task 2.2 — Add post-search zero-results clarification gate in `_orchestrate_stream()`

**File**: `fashion_agent/agent/fashion_agent.py`

**What**: After the search runs and returns zero products, check if we should ask for
clarification. This is the *only* place clarification fires for `text_search` — it replaces
the pre-search slot gate entirely.

**Why bounded**: `_count_clarification_turns(history)` counts consecutive assistant questions
already asked. Once `MAX_CLARIFICATION_TURNS` (= 3) is reached, we fall through and let the
synthesis LLM handle the zero-results state naturally with a helpful message.

**Where**: In `_orchestrate_stream()`, between the `yield ThinkingEvent("search_done", ...)`
line and the `if products: ... _session_last_results` cache block.

**Change** — insert this block after the `search_done` ThinkingEvent:
```python
    yield ThinkingEvent(
        "search_done",
        f"Found {len(products)} products...",
    )

    # ── Post-search zero-results clarification gate ─────────────────────
    if not products and intent in ("text_search", "follow_up"):
        clarify_count = _count_clarification_turns(history)
        if clarify_count < MAX_CLARIFICATION_TURNS:
            question = build_template_question(
                missing_slots=["category"],
                slots=accumulated_slots,   # ← from _resolve_search_query return
                query=query,
            )
            add_message(session_id, "assistant", question)
            yield ThinkingEvent(
                "done",
                f"No results — clarification turn "
                f"{clarify_count + 1}/{MAX_CLARIFICATION_TURNS} — "
                f"{time.time() - start_time:.1f}s",
            )
            yield OrchestrateResult(
                intent="clarification",
                session_id=session_id,
                clarification=question,
                reasoning="Zero search results — requesting more detail.",
                history=history,
                filters=intent_result.filters,
            )
            return
        # MAX_CLARIFICATION_TURNS reached — fall through to synthesis
        # which will naturally say "I couldn't find anything" in the response.
    # ───────────────────────────────────────────────────
```

**Test scenarios to verify no loops**:

1. **Rich query, good results**: Send "I want a casual blue shirt" → products shown, no clarification. ✅
2. **Vague query, 0 results**: Send "xyzzy fashion" → clarification fires once. ✅
3. **Repeat vague query 3x**: After 3 clarification turns, synthesis handles gracefully: "I couldn't find anything for 'xyzzy fashion', try...". ✅
4. **Rich query, then follow-up**: Send "casual shirt" → results. Then "something cooler?" → results with expansion. No loop. ✅

---

### Task 2.3 — Add preference injection to _route_and_execute

**File**: `fashion_agent/agent/fashion_agent.py`

**What**: Add an optional `preferences` parameter to `_route_and_execute()` and prepend the
user's top preferred colour/category to the search query as soft hints.

**Where**: `_route_and_execute()` function signature and body; call site in `_orchestrate_stream()`.

**Change 1** — update function signature:
```python
def _route_and_execute(
    intent: str,
    search_query: str,
    session_id: str,
    filters: Optional[dict] = None,
    preferences: Optional[dict] = None,   # NEW
) -> tuple[list[NodeWithScore], str]:
```

**Change 2** — add preference injection at the top of the function body, before the `if intent
in ("text_search", "follow_up"):` branch:
```python
    # Soft preference injection: append user's top colour/category as hints
    if preferences:
        pref_hints: list[str] = []
        top_color = (preferences.get("preferred_colors") or [None])[0]
        top_cat   = (preferences.get("preferred_categories") or [None])[0]
        if top_color and top_color.lower() not in search_query.lower():
            pref_hints.append(top_color)
        if top_cat and top_cat.lower() not in search_query.lower():
            pref_hints.append(top_cat)
        if pref_hints:
            search_query = search_query + " " + " ".join(pref_hints)
```

**Change 3** — update the call site in `_orchestrate_stream()` (the `_route_and_execute` call at
Step 5):
```python
products, reasoning = _route_and_execute(
    intent=intent,
    search_query=search_query,
    session_id=session_id,
    filters=intent_result.filters,
    preferences=preferences,       # NEW
)
```

**Test**: Create a session. Send "show me something in black" (preference recorded). Then send
"show me a shirt" (no colour). Verify the search query used contains "black" from preferences.
Check backend logs: `reasoning` should include `black` appended.

---

### Task 2.4 — Enable query expansion for follow_up intent

**File**: `fashion_agent/agent/fashion_agent.py`

**What**: In `_route_and_execute()`, pass `use_query_expansion=True` only for `follow_up` intent
to broaden semantically similar results.

**Where**: The `if intent in ("text_search", "follow_up"):` branch.

**Change**:
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
if intent in ("text_search", "follow_up"):
    use_expansion = (intent == "follow_up")
    products = hybrid_search(
        search_query,
        top_k=6,
        use_query_expansion=use_expansion,
        filters=filters,
    )
```

**Test**: Send a vague follow-up like "something cooler?" after a search. Verify results contain
more variety than the original query.

---

### Task 2.4 — Add proactive suggestion to synthesis prompt

**File**: `fashion_agent/agent/prompts.py`

**What**: Extend `STREAM_SYNTHESIS_PROMPT` with a paragraph instructing the model to add a
"You might also like" proactive suggestion at the end of its response.

**Where**: Find the `STREAM_SYNTHESIS_PROMPT` string constant. Append to its content (inside the
closing triple-quote) the following paragraph:

```python
# Add to STREAM_SYNTHESIS_PROMPT before the closing triple-quote:
"""

After presenting the products, if items were found, add 1–2 sentences proactively suggesting
what might pair well or what the user might want to explore next (e.g. matching trousers for a
shirt). Keep it concise, natural, and specific to the items shown. Label it as a suggestion, not
a command. Do NOT add this if no products were found.
"""
```

**Test**: Send "show me a white shirt". Verify the agent response contains a paragraph about
complementary pieces (e.g., "You might also like navy chinos to complete this look").

---

## Group 3 — Shimmer Skeleton (Frontend)

### Task 3.1 — Add shimmer package

**File**: `clothie_web/pubspec.yaml`

**What**: Add the `shimmer` package if not already present.

**Check first**: Run `grep "shimmer" clothie_web/pubspec.yaml`. If present, skip this task.

**Change**:
```yaml
dependencies:
  # ... existing ...
  shimmer: ^3.0.0
```

Then run:
```bash
cd clothie_web && flutter pub get
```

---

### Task 3.2 — Create ShimmerProductGrid widget

**File**: `clothie_web/lib/widgets/shimmer_product_grid.dart` (new file)

**What**: Create a shimmer skeleton widget that renders 6 placeholder cards in a 3-column grid,
matching the product grid layout.

```dart
import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

/// Shown while the AI agent is thinking (MessageStatus.thinking).
/// Renders a 3×2 shimmer skeleton that matches the product card grid.
class ShimmerProductGrid extends StatelessWidget {
  const ShimmerProductGrid({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final base      = isDark ? const Color(0xFF2A2A2A) : const Color(0xFFE0E0E0);
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

---

### Task 3.3 — Integrate shimmer into chat bubble

**File**: `clothie_web/lib/widgets/chat_bubble.dart` (or wherever `ChatMessage` products are
rendered)

**What**: Show `ShimmerProductGrid` when `message.status == MessageStatus.thinking` AND
`message.products.isEmpty`.

**Where**: Find the section that conditionally renders the product grid. Add the shimmer condition
above it:

```dart
import 'package:clothie_web/widgets/shimmer_product_grid.dart';

// In the bubble content Column:

// Shimmer: shown while thinking, before real products arrive
if (message.status == MessageStatus.thinking && message.products.isEmpty)
  const Padding(
    padding: EdgeInsets.only(top: 8),
    child: ShimmerProductGrid(),
  ),

// Real product grid (already exists):
if (message.products.isNotEmpty)
  ProductGrid(products: message.products),
```

**Test**: Send a search query. Verify shimmer appears for 2-4 seconds, then is replaced by real
product cards.

---

## Group 4 — Shift+Enter Multi-line Input (Frontend)

### Task 4.1 — Update chat input field

**File**: `clothie_web/lib/screens/chat_screen.dart` (or `lib/widgets/chat_input.dart`)

**What**: Wrap the send `TextField` with `CallbackShortcuts` so Shift+Enter inserts a newline
while plain Enter continues to trigger the send button.

**Find**: The `TextField` used for chat message input. It likely has `textInputAction:
TextInputAction.send` and `onSubmitted: _handleSend`.

**Change**:
```dart
// Add import at top:
import 'package:flutter/services.dart';

// Replace the TextField with:
CallbackShortcuts(
  bindings: <ShortcutActivator, VoidCallback>{
    const SingleActivator(LogicalKeyboardKey.enter, shift: true): () {
      final ctrl = _inputController;
      final text = ctrl.text;
      final sel  = ctrl.selection;
      final before = text.substring(0, sel.start);
      final after  = text.substring(sel.end);
      ctrl.value = TextEditingValue(
        text: '$before\n$after',
        selection: TextSelection.collapsed(offset: sel.start + 1),
      );
    },
  },
  child: TextField(
    controller: _inputController,
    maxLines: null,                            // allow growing height
    keyboardType: TextInputType.multiline,
    textInputAction: TextInputAction.newline,  // mobile: action key inserts newline
    onSubmitted: null,                         // disable — send via button only
    // ... keep all other decoration, style, etc. unchanged
  ),
),
```

**Note**: The `_sendMessage()` logic already exists and is wired to the send `IconButton`. With
`onSubmitted: null`, Enter on desktop does nothing for the TextField itself; Shift+Enter inserts
`\n` via the shortcut; plain Enter does nothing (the user must tap the send button or press the
send icon). This is intentional — it prevents accidental sends.

If you want plain Enter to also send (same as before, just adding Shift+Enter for newline), add:
```dart
const SingleActivator(LogicalKeyboardKey.enter): _handleSend,
```
to the `bindings` map.

**Test**: Open app in browser. Click the input. Type a line, press Shift+Enter — a new line
appears. Type another line. Press Enter or click send — message sent with both lines.

---

## Group 5 — Rating System Redesign (Backend + Frontend)

### Task 5.1 — Add new DB columns

**File**: `fashion_agent/agent/memory.py`

**What**: Add three new columns to `user_ratings` in `init_memory_tables()`.

**Where**: In the `ddl` string, find the `user_ratings` table comment section. After the existing
`CREATE TABLE IF NOT EXISTS user_ratings` block (after the `idx_user_ratings_session` index),
add:

```python
    -- Thesis evaluation v2: 1-5 scale, three targeted questions
    ALTER TABLE user_ratings
        ADD COLUMN IF NOT EXISTS rating_overall INT
            CHECK (rating_overall BETWEEN 1 AND 5);
    ALTER TABLE user_ratings
        ADD COLUMN IF NOT EXISTS rating_suggestions INT
            CHECK (rating_suggestions BETWEEN 1 AND 5);
    ALTER TABLE user_ratings
        ADD COLUMN IF NOT EXISTS rating_conversation INT
            CHECK (rating_conversation BETWEEN 1 AND 5);
```

**Test**: Restart the backend (or run `init_memory_tables()` manually). Run:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'user_ratings';
```
Verify `rating_overall`, `rating_suggestions`, `rating_conversation` appear.

---

### Task 5.2 — Update RatingRequest model and endpoint

**File**: `fashion_agent/api/main.py`

**What**: Replace the single `rating: int` field with three 1–5 fields. Update the INSERT
statement.

**Change 1** — `RatingRequest` model (currently lines 122–126):
```python
class RatingRequest(BaseModel):
    session_id: str
    rating_overall: int        # 1–5: overall experience
    rating_suggestions: int    # 1–5: were suggestions right?
    rating_conversation: int   # 1–5: how natural was the conversation?
    feedback: str = ""
```

**Change 2** — `submit_rating_endpoint` validation (currently `if not (1 <= req.rating <= 10)`):
```python
for field_name, val in [
    ("rating_overall", req.rating_overall),
    ("rating_suggestions", req.rating_suggestions),
    ("rating_conversation", req.rating_conversation),
]:
    if not (1 <= val <= 5):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be between 1 and 5",
        )
```

**Change 3** — INSERT statement:
```python
cur.execute(
    """
    INSERT INTO user_ratings
        (session_id, user_name, rating,
         rating_overall, rating_suggestions, rating_conversation,
         feedback)
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """,
    (
        req.session_id,
        user_name,
        req.rating_overall * 2,         # backward-compat: 5→10, 4→8, etc.
        req.rating_overall,
        req.rating_suggestions,
        req.rating_conversation,
        req.feedback,
    ),
)
```

**Test**: `POST /api/rating` with body:
```json
{
  "session_id": "<valid_id>",
  "rating_overall": 4,
  "rating_suggestions": 5,
  "rating_conversation": 3,
  "feedback": "Great experience!"
}
```
Expect `{"ok": true}`. Verify DB row has correct values.

---

### Task 5.3 — Update StarRating widget for maxStars

**File**: `clothie_web/lib/widgets/star_rating.dart`

**What**: Add a `maxStars` parameter (default `10`) so the widget can render 5 stars for the new
rating questions.

**Change**: Find the `StarRating` StatefulWidget. Add:
```dart
final int maxStars;

const StarRating({
  super.key,
  required this.value,
  required this.onChanged,
  this.maxStars = 10,    // default preserves existing behaviour
});
```

Update the `itemCount` in the star builder to use `maxStars` instead of the hardcoded `10`.

**Test**: Render `StarRating(value: 3, onChanged: ..., maxStars: 5)` — should show 5 stars, 3
filled.

---

### Task 5.4 — Update api_service.dart

**File**: `clothie_web/lib/services/api_service.dart`

**What**: Update `submitRating()` signature and body to send the three new fields.

**Change**:
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

---

### Task 5.5 — Update RatingScreen and RatingDialog UI

**File**: `clothie_web/lib/screens/rating_screen.dart`

**What**: Replace the single 1–10 `StarRating` block with three 1–5 rated questions.

**State changes** (in both `_RatingScreenState` and `_RatingDialogState`):
```dart
// Replace:
int _rating = 0;

// With:
int _ratingOverall = 0;
int _ratingSuggestions = 0;
int _ratingConversation = 0;
```

**Validation** in `_submit()` — replace:
```dart
// BEFORE
if (_rating == 0) {
  setState(() => _error = 'Please select a rating.');
  return;
}

// AFTER
if (_ratingOverall == 0 || _ratingSuggestions == 0 || _ratingConversation == 0) {
  setState(() => _error = 'Please answer all three questions.');
  return;
}
```

**API call** in `_submit()` — replace:
```dart
// BEFORE
await _api.submitRating(sessionId: widget.sessionId, rating: _rating, feedback: ...);

// AFTER
await _api.submitRating(
  sessionId: widget.sessionId,
  ratingOverall: _ratingOverall,
  ratingSuggestions: _ratingSuggestions,
  ratingConversation: _ratingConversation,
  feedback: _feedbackController.text.trim(),
);
```

**UI build** — replace the single `StarRating` widget with three labelled questions:
```dart
// Question 1
Text('Overall experience', style: GoogleFonts.outfit(fontSize: 13, fontWeight: FontWeight.w600)),
const SizedBox(height: 8),
StarRating(value: _ratingOverall, onChanged: (v) => setState(() => _ratingOverall = v), maxStars: 5),
const SizedBox(height: 20),

// Question 2
Text('Were the suggestions right for you?', style: GoogleFonts.outfit(fontSize: 13, fontWeight: FontWeight.w600)),
const SizedBox(height: 8),
StarRating(value: _ratingSuggestions, onChanged: (v) => setState(() => _ratingSuggestions = v), maxStars: 5),
const SizedBox(height: 20),

// Question 3
Text('How natural did the conversation feel?', style: GoogleFonts.outfit(fontSize: 13, fontWeight: FontWeight.w600)),
const SizedBox(height: 8),
StarRating(value: _ratingConversation, onChanged: (v) => setState(() => _ratingConversation = v), maxStars: 5),
```

Also update the score display text:
```dart
// BEFORE
_rating == 0 ? 'Select a score (1–10)' : 'Your score: $_rating / 10',

// AFTER — remove this text entirely (each question is self-labelled)
```

**Test**: Open the rating screen. Verify 3 labelled 5-star widgets appear. Rate each, submit.
Verify backend receives all three values. Verify redirect to RegisterScreen after success.

---

## Group 6 — Docker Rebuild

### Task 6.1 — Rebuild and restart

```bash
cd /Users/tringuyen/llm-thesis/fashion_agent

# Backend changes (Groups 1, 2, 5 backend)
docker compose build fashion-api

# Frontend changes (Groups 3, 4, 5 frontend)
docker compose build clothie-web

# Restart stack
docker compose up -d

# Verify health
curl http://localhost:8000/health
```

Expected: `{"status": "healthy", ...}`

---

## Completion Checklist

- [ ] Task 1.1 — `os.path.basename()` applied to `image_path` in SSE payload
- [ ] Task 1.2 — Dead `except` block removed
- [ ] Task 2.1 — Pre-search slot gate removed; `_resolve_search_query` returns 3 values
- [ ] Task 2.2 — Post-search zero-results clarification gate added in `_orchestrate_stream`
- [ ] Task 2.3 — Preference injection added to `_route_and_execute`
- [ ] Task 2.4 — `use_query_expansion=True` for `follow_up` intent
- [ ] Task 2.5 — Proactive synthesis prompt paragraph added
- [ ] Task 3.1 — `shimmer` package added to pubspec
- [ ] Task 3.2 — `ShimmerProductGrid` widget created
- [ ] Task 3.3 — Shimmer integrated into chat bubble
- [ ] Task 4.1 — Shift+Enter inserts newline in chat input
- [ ] Task 5.1 — New rating DB columns added
- [ ] Task 5.2 — `RatingRequest` model and endpoint updated
- [ ] Task 5.3 — `StarRating` gets `maxStars` parameter
- [ ] Task 5.4 — `api_service.dart submitRating()` updated
- [ ] Task 5.5 — `RatingScreen` and `RatingDialog` rebuilt with 3 questions
- [ ] Task 6.1 — Docker images rebuilt and stack restarted

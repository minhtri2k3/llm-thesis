# Design: Clothie UX Improvements

## Overview

Five coordinated changes across two repos (`fashion_agent/` backend + `clothie_web/` Flutter frontend). All changes are additive or narrowly scoped — no existing APIs are renamed, no DB schema changes required.

---

## 1. Gender-Aware Search Filter

### Problem
`_route_and_execute()` calls `hybrid_search()` and returns results regardless of the user's gender. The gender is stored in `user_sessions.gender` but only used later as a text hint in the LLM synthesis prompt — the LLM may or may not respect it.

### Solution: Post-search label filter

Add a `_filter_by_gender()` helper in `fashion_agent.py` that uses the same category sets already defined in `analytics.py`:

```
MALE_CATEGORIES  = {"Longsleeve", "T-Shirt", "Shirt", "Hoodie", "Shorts", "Pants", "Blazer", "Polo"}
FEMALE_CATEGORIES = {"Dress", "Skirt", "Blouse", "Top"}
```

Call site: after `hybrid_search()` returns results in `_route_and_execute()`, before returning to the orchestration layer.

```
_route_and_execute(intent, search_query, session_id, filters)
  └─ hybrid_search(...) → raw_products
  └─ _filter_by_gender(raw_products, session_id) → filtered_products
  └─ return filtered_products, reasoning
```

**Filter logic:**
- Fetch `(gender, gender_hint_enabled)` from DB.
- If `gender_hint_enabled` is `False` → skip filter (A/B control group).
- If `gender == "male"` → remove any product whose `label` is in `FEMALE_CATEGORIES`.
- If `gender == "female"` → remove any product whose `label` is in `MALE_CATEGORIES`.
- If fewer than 1 result remain after filtering → return unfiltered (safety net to never show 0 products).
- The filter is **non-fatal**: wrap in try/except, fall back to unfiltered on any DB error.

### Data flow
```
user_sessions.gender = 'male'
user_sessions.gender_hint_enabled = True
         ↓
hybrid_search("shirt", top_k=6) → [Shirt, T-Shirt, Dress, Skirt, Hoodie, Top]
         ↓
_filter_by_gender → [Shirt, T-Shirt, Hoodie]   (Dress/Skirt/Top removed)
         ↓
synthesis prompt + gender_context hint (unchanged)
```

---

## 2. Dark Mode Colour Palette

### Current vs Proposed

| Token | Current | Proposed | Rationale |
|-------|---------|----------|-----------|
| `darkBackground` | `#0C0C0C` | `#1A1A2E` | Dark indigo-grey; visible as "dark" but not pure black |
| `darkCard` | `#161616` | `#252535` | Elevated surface with perceptible contrast against background |
| `darkBotBubble` | `#232323` | `#2E2E42` | Bot chat bubble; slightly brighter than card |

Accent colours (`darkUserBubbleStart`, `darkUserBubbleEnd`, `darkUserBubbleAlt`, `darkTextPrimary`) are **unchanged** — the user said text brightness is already good; only the background/surfaces need lifting.

File: `clothie_web/lib/theme/app_colors.dart` (3 constant changes only).

---

## 3. Fullscreen Image Viewer — Cart Button

### Current dialog structure
```
Stack(fit: StackFit.expand) [
  InteractiveViewer(image)          ← fills screen
  Positioned(top-right) close btn  ← ✕
  Positioned(bottom-center) label  ← product name
]
```

### Proposed addition
Add a `Positioned(left: 20, bottom: 100)` widget containing a `FloatingActionButton.extended`:

```
Positioned(
  left: 20,
  bottom: 100,
  child: FloatingActionButton.extended(
    label: Text("Add to Cart"),
    icon: Icon(Icons.shopping_cart_rounded),
    onPressed: onAddToCart,   ← callback
  )
)
```

### Callback chain

`_showFullscreenImage` needs a new `VoidCallback onAddToCart` param. The caller (`_ProductCardState.build`) constructs it:

```dart
onAddToCart: () {
  Navigator.of(ctx).pop();  // close dialog
  onCartTap(widget.productIndex + 1);  // 1-based
}
```

`onCartTap` is a `Function(int)` passed down from `ProductCardList` → `_ProductCard`. `ProductCardList` receives it from the call site in `chat_bubble.dart`. Inside `chat_bubble.dart`, the callback calls:

```dart
context.read<ChatProvider>().sendMessage(
  "${productNumber}",   // e.g. "1"
  sessionId,
)
```

This reuses the **entire existing** `product_select → selection_confirm → selection_saved` pipeline — no new backend endpoints.

### Widget prop threading
```
ChatBubble(sessionId, message)
  └─ ProductCardList(products, sessionId, onCartTap)      ← NEW prop
       └─ _ProductCard(product, productIndex, onCartTap)  ← NEW prop
            └─ _showFullscreenImage(url, label, onAddToCart)  ← NEW param
```

---

## 4. Offer Flow (Post-Suggestion Prompt)

### Overview

After every successful product search + synthesis, the backend emits a new SSE event asking the user whether they want to proceed to checkout or keep browsing.

### Backend SSE sequence (new)

```
event: products   → {products: [...]}  (existing)
event: token      → streamed synthesis text  (existing)
event: done       → {session_id, intent, ...}  (existing)
event: offer_prompt → {text: "...", lang: "en"}  (NEW)
```

The `offer_prompt` event is emitted **after** `done`, only when `intent` is `text_search` or `follow_up` and `len(products) > 0`.

**Multilingual offer_prompt text:**
- EN: `"Would you like to place an order for these items, or continue looking? 🛍️"`
- VN: `"Bạn muốn đặt hàng những sản phẩm này không, hay muốn tiếp tục tìm thêm? 🛍️"`
- ES: `"¿Te gustaría realizar un pedido con estos artículos o seguir buscando? 🛍️"`

### User responses

**YES path (user accepts offer):**
- FE intercepts `offer_prompt` → shows dialog
- User taps "Yes" button → FE calls `CartScreen.show(ctx, sessionId, userName)` directly (no message sent to backend)
- If cart screen confirms an order → existing `order_placed` → rating flow (unchanged)

**NO path (user declines offer):**
- User taps "No" button → FE calls `ChatProvider.sendMessage("__offer_declined__", sessionId)` (private sentinel string)
- Backend detects `__offer_declined__` intent:
  - Emits `selection_cancelled` SSE with decline text
  - Emits `offer_prompt` again with re-ask text

**Re-ask text (after decline):**
- EN: `"No problem! Let me know if you'd like to look for more items, or type 'order' when you're ready to checkout. 😊"`
- VN: `"Không sao! Hãy tiếp tục tìm thêm, hoặc gõ 'đặt hàng' khi bạn sẵn sàng. 😊"`
- ES: `"¡Sin problema! Sigue buscando o escribe 'pedir' cuando estés listo para ordenar. 😊"`

### Frontend (ChatProvider)

New field on `ChatMessage`:
```dart
bool showOfferDialog = false;   // triggers dialog in ChatBubble / ChatScreen
```

New SSE handler in `_handleSseEvent`:
```dart
case 'offer_prompt':
  final text = data['text'] ?? '';
  aiMsg.content += '\n\n$text';
  aiMsg.showOfferDialog = true;
  aiMsg.status = MessageStatus.done;
```

`ChatScreen` observes `provider.messages.last.showOfferDialog` → shows `_OfferDialog`.

### `_OfferDialog` (new widget in chat_screen.dart)

Simple `AlertDialog` or `showModalBottomSheet`:
- Title: "Ready to order?" / "Sẵn sàng đặt hàng?" / "¿Listo para ordenar?"
- YES button → `CartScreen.show()`
- NO button → `provider.sendMessage("__offer_declined__", sessionId)`
- Auto-dismiss after YES/NO tap; flag cleared on dismiss.

---

## 5. CTA Text Update

Replace "Type a number (1-N) to select your favorite!" in 3 locations:

### Location 1: `_build_synthesis_context()` (line ~168)
```python
# Before
cta_example = f"👉 Type a number (1-{len(products)}) to select your favorite!"
# After
if lang == "vi":
    cta_example = "👉 Hãy cho tôi biết bạn thích cái nào — tôi sẽ thêm vào giỏ hàng ngay!"
elif lang == "es":
    cta_example = "👉 Dime cuál te gusta, ¡lo añadiré al carrito!"
else:
    cta_example = "👉 Tell me which one you like — I'll add it to your cart!"
```

### Location 2: `chat_stream()` agentic mode (line ~1271)
Same trilingual approach replacing the `cta` variable.

### Location 3: `_handle_reject()` (line ~894)
```python
# Before
lines = ["❌ Selection cancelled. Here are the items again. Type a number to select a different one!\n"]
# After (per language)
EN: "❌ No problem! Here are the items again — tell me which one you'd like to add to your cart."
VN: "❌ Không sao! Đây là các sản phẩm — hãy cho tôi biết bạn muốn thêm cái nào vào giỏ hàng."
ES: "❌ ¡Sin problema! Aquí están los artículos — dime cuál quieres añadir al carrito."
```

---

## Docker Rebuild Plan

After all code changes:
1. `docker compose build fashion-api` → push updated backend
2. `docker compose build clothie-web` → push updated Flutter build
3. `docker compose up -d` → restart affected containers

No DB migrations required (no schema changes).

---

## Risk & Mitigations

| Risk | Mitigation |
|------|------------|
| Gender filter removes ALL results for a valid query | Safety net: if `len(filtered) == 0`, return unfiltered results |
| `offer_prompt` emitted for non-search intents | Guard: only emit when `intent in ("text_search", "follow_up") and products` |
| `__offer_declined__` sentinel leaks to user | Intent classifier catches it before synthesis; never reaches LLM |
| Prop threading in Flutter breaks existing build | Add `onCartTap` as nullable with default no-op to keep all existing call sites valid |

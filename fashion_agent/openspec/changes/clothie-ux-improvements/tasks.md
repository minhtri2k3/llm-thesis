# Tasks: Clothie UX Improvements

## Status: ✅ All tasks implemented

---

## Task 1 — Gender-Aware Post-Search Filter (Backend)
**File:** `fashion_agent/agent/fashion_agent.py`
**Complexity:** Low

### Steps
1. Import `MALE_CATEGORIES` / `FEMALE_CATEGORIES` from `api/analytics.py` (or redefine inline to avoid circular import).
2. Add `_filter_by_gender(products, session_id) -> list[NodeWithScore]` helper:
   - Calls `get_session_gender(session_id)` → `(gender, hint_enabled)`.
   - Returns `products` unchanged if `not hint_enabled` or `gender is None`.
   - Filters out products whose `label` is in the wrong gender set.
   - Safety net: if `len(filtered) == 0` return `products` (unfiltered).
   - Wrap entire function in `try/except Exception: return products`.
3. In `_route_and_execute()`: after `hybrid_search()` call, apply `_filter_by_gender(products, session_id)`.

### Acceptance
- `_filter_by_gender([Dress, Shirt, Skirt], session_id_of_male_user)` returns `[Shirt]`.
- If `gender_hint_enabled=False`, results are unchanged.
- Function never raises (caught exception → unfiltered fallback).

---

## Task 2 — Dark Mode Colour Palette (Frontend)
**File:** `clothie_web/lib/theme/app_colors.dart`
**Complexity:** Trivial

### Steps
1. Change `darkBackground` from `Color(0xFF0C0C0C)` → `Color(0xFF1A1A2E)`.
2. Change `darkCard` from `Color(0xFF161616)` → `Color(0xFF252535)`.
3. Change `darkBotBubble` from `Color(0xFF232323)` → `Color(0xFF2E2E42)`.

### Acceptance
- In dark mode, the background is visibly grey/indigo (not pure black) on a calibrated screen.
- Card surfaces have perceptible contrast against the background.
- Accent / text colours are unchanged.

---

## Task 3 — CTA Text Update (Backend)
**File:** `fashion_agent/agent/fashion_agent.py`
**Complexity:** Low

### Steps
Update 3 locations (search with "Type a number"):

**Location A** — `_build_synthesis_context()` (~line 163-168):
```python
if lang == "vi":
    cta_example = "👉 Hãy cho tôi biết bạn thích cái nào — tôi sẽ thêm vào giỏ hàng ngay!"
elif lang == "es":
    cta_example = "👉 Dime cuál te gusta, ¡lo añadiré al carrito!"
else:
    cta_example = "👉 Tell me which one you like — I'll add it to your cart!"
```

**Location B** — `chat_stream()` agentic mode CTA (~line 1267-1271):
Apply the same trilingual replacement for the `cta` variable.

**Location C** — `_handle_reject()` (~line 893-894):
```python
# EN
lines = ["❌ No problem! Here are the items again — tell me which one you'd like to add to your cart.\n"]
# VN
lines = ["❌ Không sao! Đây là các sản phẩm — hãy cho tôi biết bạn muốn thêm cái nào vào giỏ hàng.\n"]
# ES
lines = ["❌ ¡Sin problema! Aquí están los artículos — dime cuál quieres añadir al carrito.\n"]
```

### Acceptance
- English session: CTA ends with "...I'll add it to your cart!"
- Vietnamese session: CTA contains "giỏ hàng"
- Spanish session: CTA contains "carrito"

---

## Task 4 — Fullscreen Cart Button (Frontend)
**Files:** `clothie_web/lib/widgets/product_card.dart`, `clothie_web/lib/widgets/chat_bubble.dart`
**Complexity:** Medium

### Steps

**4a. `product_card.dart`**

1. Add `onCartTap` param to `ProductCardList`: `final Function(int)? onCartTap;`
2. Pass `onCartTap` down to `_ProductCard`: add `final Function(int)? onCartTap;`
3. In `_ProductCard.build()`, pass to GestureDetector's `onTap` for `_showFullscreenImage`:
   ```dart
   onAddToCart: widget.onCartTap != null
       ? () { Navigator.pop(ctx); widget.onCartTap!(widget.productIndex + 1); }
       : null,
   ```
4. In `_showFullscreenImage()`, add `VoidCallback? onAddToCart` param.
5. Inside the `Stack`, add:
   ```dart
   if (onAddToCart != null)
     Positioned(
       left: 20,
       bottom: 100,
       child: Material(
         color: Colors.transparent,
         child: FloatingActionButton.extended(
           backgroundColor: Theme.of(ctx).colorScheme.primary,
           foregroundColor: Theme.of(ctx).colorScheme.onPrimary,
           icon: const Icon(Icons.shopping_cart_rounded),
           label: const Text("Add to Cart"),
           onPressed: onAddToCart,
         ),
       ),
     ),
   ```

**4b. `chat_bubble.dart`**

1. In the `ProductCardList(...)` call site, add `onCartTap`:
   ```dart
   ProductCardList(
     products: message.products,
     sessionId: sessionId,
     onCartTap: (num) {
       context.read<ChatProvider>().sendMessage("$num", sessionId);
     },
   )
   ```

### Acceptance
- Tapping "Add to Cart" in the fullscreen view closes the dialog and sends the product number as a chat message.
- The chat responds with a `selection_confirm` bubble (existing flow).
- If `onCartTap` is null (e.g., test widget), the FAB is not shown.

---

## Task 5 — Offer Prompt Flow (Backend + Frontend)
**Complexity:** High

### 5a. Backend — Emit `offer_prompt` SSE (`fashion_agent.py`)

1. After the `yield _sse("done", {...})` call in `chat_stream()`, add:
   ```python
   if result.intent in ("text_search", "follow_up") and len(result.products) > 0:
       lang = detect_language(query)
       offer_texts = {
           "vi": "Bạn muốn đặt hàng những sản phẩm này không, hay muốn tiếp tục tìm thêm? 🛍️",
           "es": "¿Te gustaría realizar un pedido con estos artículos o seguir buscando? 🛍️",
           "en": "Would you like to place an order for these items, or continue looking? 🛍️",
       }
       offer_text = offer_texts.get(lang, offer_texts["en"])
       yield _sse("offer_prompt", {"text": offer_text, "lang": lang})
   ```

### 5b. Backend — Handle `__offer_declined__` sentinel (`fashion_agent.py`)

1. In `_orchestrate_stream()`, before intent classification, check:
   ```python
   if query.strip() == "__offer_declined__":
       yield from _handle_offer_declined(session_id, query)
       return
   ```
2. Add `_handle_offer_declined(session_id, query) -> Generator`:
   ```python
   lang = detect_language_from_session(session_id)  # or default 'en'
   decline_texts = {
       "vi": "Không sao! Hãy tiếp tục tìm thêm, hoặc gõ 'đặt hàng' khi bạn sẵn sàng. 😊",
       "es": "¡Sin problema! Sigue buscando o escribe 'pedir' cuando estés listo. 😊",
       "en": "No problem! Keep browsing, or say 'order' whenever you're ready to checkout. 😊",
   }
   text = decline_texts.get(lang, decline_texts["en"])
   add_message(session_id, "assistant", text)
   yield _sse("clarification", {"text": text, "intent": "offer_declined"})
   yield _sse("done", {"session_id": session_id, "intent": "offer_declined", "styling": ""})
   ```

### 5c. Frontend — Handle `offer_prompt` SSE (`chat_provider.dart`)

1. On `ChatMessage`, add:
   ```dart
   bool showOfferDialog = false;
   ```
2. In `_handleSseEvent`, add:
   ```dart
   case 'offer_prompt':
     final text = data is Map ? (data['text'] as String? ?? '') : '';
     if (text.isNotEmpty) aiMsg.content += '\n\n$text';
     aiMsg.showOfferDialog = true;
     aiMsg.status = MessageStatus.done;
   ```

### 5d. Frontend — Offer Dialog (`chat_screen.dart`)

1. After building the message list, check last message:
   ```dart
   final lastMsg = provider.messages.isNotEmpty ? provider.messages.last : null;
   if (lastMsg != null && lastMsg.showOfferDialog && !_offerDialogShown) {
     _offerDialogShown = true;
     WidgetsBinding.instance.addPostFrameCallback((_) => _showOfferDialog(context, provider));
   }
   ```
2. Add `bool _offerDialogShown = false;` to `_ChatScreenState`.  
   Reset to `false` whenever `provider.messages` changes length (new search cycle).
3. Implement `_showOfferDialog(context, provider)`:
   ```dart
   showDialog(
     context: context,
     barrierDismissible: false,
     builder: (ctx) => AlertDialog(
       title: Text("Ready to order? 🛍️"),
       content: Text("Place an order for the items above, or keep browsing?"),
       actions: [
         TextButton(
           onPressed: () {
             Navigator.pop(ctx);
             CartScreen.show(context, widget.sessionId, widget.userName);
           },
           child: Text("Order now"),
         ),
         TextButton(
           onPressed: () {
             Navigator.pop(ctx);
             provider.sendMessage("__offer_declined__", widget.sessionId);
           },
           child: Text("Keep browsing"),
         ),
       ],
     ),
   );
   ```
   > Note: Use the session language detected on the FE (or pass lang from `offer_prompt` SSE data) for trilingual dialog text.

### Acceptance
- After a successful product search in EN, a dialog appears: "Ready to order?"
- Tapping "Order now" opens the cart screen without any backend message.
- Tapping "Keep browsing" sends `__offer_declined__` → agent replies with re-ask text → no new offer dialog shown.
- The dialog does not appear for clarification responses, out-of-scope replies, or selection flows.

---

## Task 6 — Docker Rebuild & Verification

### Steps
1. `cd fashion_agent && docker compose build fashion-api`
2. `docker compose build clothie-web`
3. `docker compose up -d`
4. Manual smoke test:
   - Register as "男" gender=male → search "skirt" → confirm 0 skirts returned.
   - Toggle dark mode → verify background is visible grey.
   - Search for any item → click fullscreen → verify cart FAB appears.
   - Search → wait for offer dialog → tap "Keep browsing" → verify agent re-ask.
   - Search → wait for offer dialog → tap "Order now" → verify cart screen opens.
   - Check CTA text in EN, VN, ES.

### Acceptance
- `docker compose up -d` completes without errors after rebuild.
- All 5 features pass smoke test.

---

## Implementation Order

```
Task 1 (gender filter BE)     → independent, no FE dependency
Task 2 (dark mode colours)    → independent, trivial
Task 3 (CTA text)             → independent
Task 4 (fullscreen cart btn)  → FE only, independent
Task 5 (offer flow BE+FE)     → depends on Task 3 CTA text being done
Task 6 (Docker rebuild)       → after all above
```

Recommended parallel execution: Tasks 1, 2, 3, 4 can be done simultaneously. Task 5 after Task 3. Task 6 last.

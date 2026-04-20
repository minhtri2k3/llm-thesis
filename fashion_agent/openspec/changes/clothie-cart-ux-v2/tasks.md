# Tasks: Clothie Cart UX v2

## Status: ✅ Done

---

## Implementation Order

```
Task 1 (always-on gender filter BE)   → independent, 1-line change
Task 2 (pre-confirm dialog FE)        → requires chat_provider + product_card + chat_bubble
Task 3 (offer dialog upgrade FE)      → requires chat_screen only
Task 4 (Docker rebuild)               → after all above
```

Tasks 1, 2, 3 can be parallelised. Task 4 last.

---

## Task 1 — Always-On Gender Filter (Backend)

**File:** `fashion_agent/agent/memory.py`
**Complexity:** Trivial (1 line)

### Steps

1. Locate `create_session()` function (line ~315).
2. Find the block:
   ```python
   if gender_hint_enabled is None:
       gender_hint_enabled = random.random() < 0.5
   ```
3. Replace with:
   ```python
   if gender_hint_enabled is None:
       gender_hint_enabled = (gender is not None)
   ```
4. Remove `import random` if it is no longer used anywhere else in the file (check first).

### Acceptance

- New session with `gender="male"` → `gender_hint_enabled=True` in DB (confirm via `SELECT gender_hint_enabled FROM user_sessions ORDER BY created_at DESC LIMIT 1;`).
- New session with `gender=None` → `gender_hint_enabled=False` in DB.
- Existing sessions in DB are untouched.
- Male user now receives ZERO dresses/skirts for any query (safety net: if all results are filtered, unfiltered list is returned).

---

## Task 2 — Pre-Confirm Inline Dialog (Frontend)

**Files:** `clothie_web/lib/providers/chat_provider.dart`, `clothie_web/lib/widgets/product_card.dart`, `clothie_web/lib/widgets/chat_bubble.dart`
**Complexity:** Medium

### Steps

#### 2a. `chat_provider.dart` — add autoConfirmNext flag

1. Add two new fields to `ChatProvider`:
   ```dart
   bool autoConfirmNext = false;
   bool _pendingAutoConfirm = false;
   ```

2. In `_handleSseEvent`, modify the `selection_confirm` case:
   ```dart
   case 'selection_confirm':
     if (autoConfirmNext) {
       // Suppress visible bubble — auto-confirm silently
       autoConfirmNext = false;
       _pendingAutoConfirm = true;
       aiMsg.status = MessageStatus.done;
       // Do NOT set aiMsg.content or aiMsg.confirmItems
       return;  // skip rest of case
     }
     // === existing confirm logic below (unchanged) ===
     if (data is Map) {
       final rawText = data['text'] as String? ?? '';
       aiMsg.content = rawText.replaceAll(RegExp(r'!\[.*?\]\([^)]*\)'), '').trim();
       final rawItems = data['items'] as List? ?? [];
       aiMsg.confirmItems = rawItems
           .whereType<Map<String, dynamic>>()
           .map(CartItem.fromAgentJson)
           .toList();
     }
     aiMsg.status = MessageStatus.done;
   ```

3. In the `done` case, add auto-confirm trigger:
   ```dart
   case 'done':
     if (data is Map) {
       final tip = data['styling_tip'] as String?;
       if (tip != null && tip.isNotEmpty) aiMsg.stylingTip = tip;
     }
     // Auto-confirm: fire "yes" after the stream completes
     if (_pendingAutoConfirm) {
       _pendingAutoConfirm = false;
       final sid = data is Map ? (data['session_id'] as String? ?? '') : '';
       if (sid.isNotEmpty) {
         Future.microtask(() => sendMessage('yes', sid));
       }
     }
     aiMsg.status = MessageStatus.done;
   ```

4. In the `error` case, add safety reset:
   ```dart
   case 'error':
     autoConfirmNext = false;
     _pendingAutoConfirm = false;
     // ... existing error handling ...
   ```

#### 2b. `product_card.dart` — open pre-confirm dialog from FAB

1. Add a new method `_showAddToCartDialog` to `_ProductCardState`:
   ```dart
   void _showAddToCartDialog(
     BuildContext context,
     Product product,
     VoidCallback onConfirm,
   ) {
     showDialog<void>(
       context: context,
       builder: (ctx) => AlertDialog(
         shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
         title: const Text('🛒 Add to cart?'),
         content: Row(
           children: [
             ClipRRect(
               borderRadius: BorderRadius.circular(8),
               child: Image.network(
                 product.imageUrl,
                 width: 72,
                 height: 72,
                 fit: BoxFit.cover,
                 errorBuilder: (_, __, ___) => Container(
                   width: 72, height: 72,
                   color: Theme.of(context).colorScheme.surfaceVariant,
                   child: Icon(Icons.checkroom),
                 ),
               ),
             ),
             const SizedBox(width: 12),
             Expanded(
               child: Column(
                 mainAxisSize: MainAxisSize.min,
                 crossAxisAlignment: CrossAxisAlignment.start,
                 children: [
                   Text(product.label,
                       style: const TextStyle(fontWeight: FontWeight.w700)),
                   if (product.color.isNotEmpty)
                     Text(product.color,
                         style: TextStyle(
                             fontSize: 12,
                             color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6))),
                 ],
               ),
             ),
           ],
         ),
         actions: [
           TextButton(
             onPressed: () => Navigator.pop(ctx),
             child: const Text('Cancel'),
           ),
           FilledButton(
             onPressed: () { Navigator.pop(ctx); onConfirm(); },
             child: const Text('Add to Cart ✓'),
           ),
         ],
       ),
     );
   }
   ```

2. In `_showFullscreenImage`, change the FAB `onPressed`:
   ```dart
   // Old:
   onPressed: onAddToCart,

   // New:
   onPressed: () {
     Navigator.pop(ctx);  // close fullscreen
     _showAddToCartDialog(context, widget.product, () {
       widget.onCartTap!(widget.productIndex + 1);
     });
   },
   ```

   Note: The fullscreen is already closed before showing the dialog — this avoids a nested Navigator issue.

#### 2c. `chat_bubble.dart` — set autoConfirmNext before sending

In the `ProductCardList` `onCartTap` callback:
```dart
onCartTap: (num) {
  final chatProvider = context.read<ChatProvider>();
  chatProvider.autoConfirmNext = true;   // NEW — must be set BEFORE sendMessage
  chatProvider.sendMessage('$num', sessionId);
},
```

### Acceptance

- Tapping "Add to Cart" FAB in fullscreen → fullscreen closes → pre-confirm dialog appears with product image, label, color.
- Tapping "Cancel" in dialog → nothing happens; product grid still visible.
- Tapping "Add to Cart ✓" → dialog closes → NO confirm chat bubble in chat → top banner "Added to your cart 🛍️" appears.
- Typing a number in the chat input (without using FAB) → normal confirm bubble still appears (autoConfirmNext not set).

---

## Task 3 — Offer Dialog with Product Mini-Preview (Frontend)

**File:** `clothie_web/lib/screens/chat_screen.dart`
**Complexity:** Low

### Steps

1. Add `Product` import at top of file (if not already present):
   ```dart
   import 'package:clothie_web/models/product.dart';
   ```

2. Update the offer dialog trigger in `build()` to pass products:
   ```dart
   // Old:
   WidgetsBinding.instance.addPostFrameCallback(
     (_) => _showOfferDialog(context, provider),
   );

   // New:
   final offerProducts = lastMsg.products;  // same list shown in chat
   WidgetsBinding.instance.addPostFrameCallback(
     (_) => _showOfferDialog(context, provider, offerProducts),
   );
   ```

3. Update `_showOfferDialog` signature:
   ```dart
   void _showOfferDialog(
     BuildContext context,
     ChatProvider provider,
     List<Product> products,   // NEW param
   )
   ```

4. Replace the `AlertDialog` inside `_showOfferDialog` with a `Dialog` containing the product thumbnail strip:
   ```dart
   showDialog<void>(
     context: context,
     barrierDismissible: false,
     builder: (ctx) => Dialog(
       shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
       child: Padding(
         padding: const EdgeInsets.fromLTRB(20, 24, 20, 16),
         child: Column(
           mainAxisSize: MainAxisSize.min,
           crossAxisAlignment: CrossAxisAlignment.start,
           children: [
             Text('🛍️ Ready to order?',
                 style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.w700)),
             const SizedBox(height: 14),
             // Product thumbnail strip
             if (products.isNotEmpty)
               SizedBox(
                 height: 100,
                 child: ListView.separated(
                   scrollDirection: Axis.horizontal,
                   itemCount: products.length,
                   separatorBuilder: (_, __) => const SizedBox(width: 8),
                   itemBuilder: (_, i) {
                     final p = products[i];
                     return Column(
                       children: [
                         ClipRRect(
                           borderRadius: BorderRadius.circular(8),
                           child: Image.network(
                             p.imageUrl,
                             width: 64,
                             height: 72,
                             fit: BoxFit.cover,
                             errorBuilder: (_, __, ___) => Container(
                               width: 64, height: 72,
                               color: Theme.of(context).colorScheme.surfaceVariant,
                               child: const Icon(Icons.checkroom),
                             ),
                           ),
                         ),
                         const SizedBox(height: 4),
                         SizedBox(
                           width: 64,
                           child: Text(
                             p.label,
                             maxLines: 1,
                             overflow: TextOverflow.ellipsis,
                             style: GoogleFonts.outfit(fontSize: 10, fontWeight: FontWeight.w600),
                             textAlign: TextAlign.center,
                           ),
                         ),
                       ],
                     );
                   },
                 ),
               ),
             const SizedBox(height: 14),
             Text(
               'Would you like to place an order for these items, or continue looking?',
               style: GoogleFonts.outfit(fontSize: 13, height: 1.5),
             ),
             const SizedBox(height: 20),
             Row(
               mainAxisAlignment: MainAxisAlignment.end,
               children: [
                 TextButton(
                   onPressed: () {
                     Navigator.pop(ctx);
                     provider.sendMessage('__offer_declined__', widget.sessionId);
                   },
                   child: const Text('Keep browsing'),
                 ),
                 const SizedBox(width: 8),
                 FilledButton.icon(
                   onPressed: () async {
                     Navigator.pop(ctx);
                     final placed = await CartScreen.show(
                       context, widget.sessionId, widget.userName,
                     );
                     if (placed == true && context.mounted) _showRatingDialog(context);
                   },
                   icon: const Icon(Icons.shopping_cart_rounded, size: 16),
                   label: const Text('Order now'),
                 ),
               ],
             ),
           ],
         ),
       ),
     ),
   );
   ```

### Acceptance

- After a successful product search, the offer dialog shows a horizontal strip of product thumbnails (images + label below each).
- "Order now" opens `CartScreen`, and if an order is placed, the rating dialog follows.
- "Keep browsing" sends `__offer_declined__` as before.
- If `products` is empty (edge case), the thumbnail strip is hidden and the dialog shows only text + buttons.

---

## Task 4 — Docker Rebuild & Verification

### Steps

1. `cd fashion_agent && docker compose build fashion-api`
2. `docker compose build clothie-web`
3. `docker compose up -d`
4. Manual smoke test:
   - Register with gender=male → search "skirt" → confirm 0 skirts returned (safety net allows if ALL results would be filtered).
   - Register with gender=male → search "shirt" → confirm only male-category items shown (Shirt, T-Shirt, Longsleeve, etc.).
   - Search for any item → click product → open fullscreen → tap "Add to Cart" FAB → confirm pre-confirm dialog appears with image + label.
   - Tap "Cancel" → nothing happens, no chat message sent.
   - Tap "Add to Cart ✓" → confirm no text-based confirm bubble → confirm "Added to your cart" banner appears.
   - Search → wait for offer dialog → confirm product thumbnails appear in dialog.
   - Tap "Order now" → confirm cart screen opens.
   - Tap "Keep browsing" → confirm agent re-asks → offer dialog does NOT re-appear.

### Acceptance

- `docker compose up -d` starts without errors.
- All smoke tests pass.

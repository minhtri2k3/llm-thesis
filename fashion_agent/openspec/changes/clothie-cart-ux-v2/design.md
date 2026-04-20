# Design: Clothie Cart UX v2

## Overview

Three coordinated fixes across the backend (`fashion_agent/`) and Flutter frontend (`clothie_web/`).
All changes are minimal and additive — no DB migrations, no new SSE event types, no new API endpoints.

---

## 1. Pre-confirm Inline Dialog (Add to Cart)

### Current flow (problem)

```
User taps "Add to Cart" FAB
         │
         ▼  (immediate)
sendMessage("1", sessionId)
         │
         ▼  backend
selection_confirm SSE
         │
         ▼  FE renders confirm chat bubble:
"✅ You selected:
 1. Shirt — Cream
 _description..._
 Confirm? (yes/no)"
         │
         ▼  user types "yes"
         │
         ▼  selection_saved SSE → top banner
```

### Desired flow

```
User taps "Add to Cart" FAB
         │
         ▼  (FE only, no backend call)
┌───────────────────────────────┐
│  🛒 Add to cart?              │
│  ┌──────────┐                 │
│  │ [image]  │  Shirt — Cream  │
│  └──────────┘                 │
│                               │
│  [Cancel]    [Add to Cart ✓]  │
└───────────────────────────────┘
         │ user taps [Add to Cart ✓]
         ▼
chatProvider.autoConfirmNext = true
sendMessage("1", sessionId)
         │
         ▼  backend
selection_confirm SSE received
         │
         ▼  FE detects autoConfirmNext=true:
            - clears confirm bubble (no visible render)
            - resets autoConfirmNext = false
            - sendMessage("yes", sessionId)  ← silent
         │
         ▼  selection_saved SSE
         │
         ▼  top banner: "Added to your cart 🛍️"
```

### State changes per file

#### `lib/providers/chat_provider.dart`

New field:
```dart
bool autoConfirmNext = false;
```

In `_handleSseEvent`, add early-exit branch for `selection_confirm`:
```dart
case 'selection_confirm':
  if (autoConfirmNext) {
    // Suppress bubble, auto-confirm silently
    autoConfirmNext = false;
    // Fire "yes" after current stream completes (post-done)
    _pendingAutoConfirm = true;
    aiMsg.status = MessageStatus.done;
    // content and confirmItems left empty → bubble renders nothing
    return;
  }
  // Normal path (user typed a number manually):
  // ... existing code to set aiMsg.content, confirmItems, status ...
```

New field `_pendingAutoConfirm` flag — checked in the `done` handler:
```dart
case 'done':
  aiMsg.status = MessageStatus.done;
  if (_pendingAutoConfirm) {
    _pendingAutoConfirm = false;
    // The session_id is available via the done payload
    final sid = data is Map ? (data['session_id'] as String? ?? '') : '';
    if (sid.isNotEmpty) {
      Future.microtask(() => sendMessage('yes', sid));
    }
  }
```

Safety reset — also set `autoConfirmNext = false` on any `error` or `done` event to prevent stale flag.

#### `lib/widgets/product_card.dart`

Current `onTap` in FAB:
```dart
onPressed: onAddToCart,  // calls onCartTap directly
```

New: FAB `onPressed` opens a pre-confirm dialog:
```dart
onPressed: () {
  Navigator.pop(ctx);  // close fullscreen first
  _showAddToCartDialog(context, widget.product, onAddToCart!);
},
```

New method `_showAddToCartDialog`:
```dart
void _showAddToCartDialog(
  BuildContext context,
  Product product,
  VoidCallback onConfirm,
) {
  showDialog(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text('🛒 Add to cart?'),
      content: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: Image.network(product.imageUrl, width: 72, height: 72, fit: BoxFit.cover),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(product.label, style: TextStyle(fontWeight: FontWeight.w700)),
                if (product.color.isNotEmpty)
                  Text(product.color, style: TextStyle(fontSize: 12, color: Colors.grey)),
              ],
            ),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: Text('Cancel')),
        FilledButton(
          onPressed: () { Navigator.pop(ctx); onConfirm(); },
          child: Text('Add to Cart ✓'),
        ),
      ],
    ),
  );
}
```

No changes to `chat_bubble.dart` — the `onCartTap` callback chain is unchanged.

### Widget call-site change

In `chat_bubble.dart`, the `onCartTap` callback is:
```dart
onCartTap: (num) {
  context.read<ChatProvider>().autoConfirmNext = true;  // NEW
  context.read<ChatProvider>().sendMessage('$num', sessionId);
},
```

Setting `autoConfirmNext` BEFORE sending the message ensures it is already `true` when the SSE response arrives.

---

## 2. Offer Dialog with Product Mini-Preview

### Current dialog (plain text)

```dart
AlertDialog(
  title: Text('🖋️ Ready to order?'),
  content: Text('Would you like to place an order...'),
  actions: [Order now, Keep browsing],
)
```

### Upgraded dialog

```
┌──────────────────────────────────────────────┐
│  🛍️ Ready to order?                          │
├──────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│  │[img] │ │[img] │ │[img] │ │[img] │  ...   │
│  │Shirt │ │Pants │ │Shirt │ │Pants │        │
│  └──────┘ └──────┘ └──────┘ └──────┘        │
│                                              │
│  Would you like to place an order for these  │
│  items, or continue looking? 🛍️             │
├──────────────────────────────────────────────┤
│        [Keep browsing]    [Order now 🛒]     │
└──────────────────────────────────────────────┘
```

### Changes to `lib/screens/chat_screen.dart`

#### Pass products into _showOfferDialog

```dart
// where the dialog is triggered:
final products = lastMsg.products;  // already populated
WidgetsBinding.instance.addPostFrameCallback(
  (_) => _showOfferDialog(context, provider, products),
);
```

#### Updated _showOfferDialog signature and body

```dart
void _showOfferDialog(
  BuildContext context,
  ChatProvider provider,
  List<Product> products,
) {
  if (!mounted) return;
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
            // Title
            Text('🛍️ Ready to order?', style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 14),
            // Product thumbnail strip
            if (products.isNotEmpty)
              SizedBox(
                height: 96,
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
                          child: Image.network(p.imageUrl, width: 64, height: 72, fit: BoxFit.cover),
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
            // Body text
            Text(
              'Would you like to place an order for these items, or continue looking?',
              style: GoogleFonts.outfit(fontSize: 13, height: 1.5),
            ),
            const SizedBox(height: 20),
            // Action buttons
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
                    final placed = await CartScreen.show(context, widget.sessionId, widget.userName);
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
}
```

---

## 3. Always-On Gender Filter

### Problem

```python
# memory.py line 334-335 — current
if gender_hint_enabled is None:
    gender_hint_enabled = random.random() < 0.5  ← 50/50 coin flip
```

When the coin lands on `False`, `_filter_by_gender()` in `fashion_agent.py` skips all filtering:
```python
if not hint_enabled or not gender:
    return products  ← unfiltered
```

### Fix

```python
# memory.py — new
if gender_hint_enabled is None:
    gender_hint_enabled = (gender is not None)
    # True  → user declared a gender → always filter
    # False → anonymous user → nothing to filter
```

### Data impact

| Aspect | Before | After |
|--------|--------|-------|
| DB schema | unchanged | unchanged |
| Historic session data | preserved with original random values | preserved |
| `/api/analytics/gender-ab` endpoint | still valid for historic data | still valid |
| New sessions with gender | `True` 50% of the time | `True` always |
| New sessions without gender | `False` always | `False` always (same) |

The `gender_context` synthesis hint (LLM text prompt) already uses the same `hint_enabled` flag — it will also now always be included for gendered users, which means **both** the hard post-search filter AND the soft LLM hint are always active for gendered sessions.

---

## Docker Rebuild Plan

1. `docker compose build fashion-api` (memory.py change in backend)
2. `docker compose build clothie-web` (Flutter widget + provider changes)
3. `docker compose up -d`

No DB migrations required.

---

## Risk & Mitigations

| Risk | Mitigation |
|------|------------|
| `autoConfirmNext` flag left `true` after stream error | Reset flag on `done` and `error` SSE events; also reset when `sendMessage` throws |
| `autoConfirmNext` flag triggered by a manual typed number (not FAB) | Only set from the FAB `onCartTap` callback in `chat_bubble.dart`; typing a number in chat does NOT set it |
| Offer dialog shows no products (empty list) | Guard: `if (products.isNotEmpty)` — if empty, dialog still shows text and buttons, thumbnail strip is hidden |
| Gender filter removes all results for valid query | Existing safety net unchanged: `if len(filtered) == 0: return products` |
| Offer dialog products differ from what user sees in chat | Products are read from `lastMsg.products` in the same render cycle — always the same set |

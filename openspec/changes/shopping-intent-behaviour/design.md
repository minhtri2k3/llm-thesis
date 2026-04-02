# Design: Shopping Intent & Behaviour Stress Test

## Architecture Overview

This change is **purely additive** — no existing tables, endpoints, or Flutter screens are removed or fundamentally altered. All new DB columns use `ADD COLUMN IF NOT EXISTS`; all new tables use `CREATE TABLE IF NOT EXISTS`. This means zero risk of breaking the running demo.

```
┌──────────────────────────────────────────────────────┐
│                    Flutter (clothie_web)              │
│                                                       │
│  chat_screen.dart           cart_screen.dart          │
│  ├─ _buildTopBanner()  →    ├─ Intent buttons         │
│  │    updated text           │   (✓ / ✗ per card)    │
│  │                          ├─ "Let's make the order" │
│  │                          │    CTA button           │
│  │                          └─ OrderDialog()          │
│  └─ chat_provider.dart                                │
│       auto-log impressions                            │
│       when 'products' SSE fires                       │
└─────────────────────┬────────────────────────────────┘
                      │ HTTP
┌─────────────────────▼────────────────────────────────┐
│                  FastAPI (fashion_agent)               │
│                                                       │
│  POST /api/sessions/{id}/impressions  (new)           │
│  POST /api/sessions/{id}/intents      (new)           │
│  POST /api/sessions/{id}/orders       (new)           │
│  GET  /api/analytics/behaviour-funnel (new)           │
│                                                       │
│  agent/memory.py                                      │
│  └─ init_memory_tables() extended with 3 new tables   │
└─────────────────────┬────────────────────────────────┘
                      │ psycopg2
┌─────────────────────▼────────────────────────────────┐
│                   PostgreSQL                           │
│                                                       │
│  product_impressions   (new)                          │
│  product_intents       (new)                          │
│  user_orders           (new)                          │
└──────────────────────────────────────────────────────┘
```

---

## Database Schema (new tables)

### `product_impressions`
Auto-logged by the Flutter client every time a `products` SSE arrives.

```sql
CREATE TABLE IF NOT EXISTS product_impressions (
    id           BIGSERIAL PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
    image_id     VARCHAR NOT NULL,
    search_query TEXT NOT NULL DEFAULT '',
    position     INT NOT NULL DEFAULT 0,        -- 1-based rank in result list
    shown_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_impressions_session
    ON product_impressions(session_id, shown_at);
```

### `product_intents`
Written when user taps `✓ I'll buy this` or `✗ Not for me` in `CartScreen`.

```sql
CREATE TABLE IF NOT EXISTS product_intents (
    id            BIGSERIAL PRIMARY KEY,
    session_id    TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
    image_id      VARCHAR NOT NULL,
    intent_type   TEXT NOT NULL CHECK (intent_type IN ('will_buy', 'not_for_me')),
    reason        TEXT NOT NULL DEFAULT '',     -- qualitative (optional)
    logged_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, image_id, intent_type)
);

CREATE INDEX IF NOT EXISTS idx_intents_session
    ON product_intents(session_id, logged_at);
```

### `user_orders`
Written when user submits the "Place Order" form (phone + address).

```sql
CREATE TABLE IF NOT EXISTS user_orders (
    id          SERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
    phone       TEXT NOT NULL DEFAULT '',
    address     TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_session
    ON user_orders(session_id);
```

---

## API Endpoints

### `POST /api/sessions/{session_id}/impressions`
**Purpose:** Batch-log all products shown in one search result.

Request body:
```json
{
  "items": [
    { "image_id": "abc123", "search_query": "white shirt", "position": 1 },
    { "image_id": "def456", "search_query": "white shirt", "position": 2 }
  ]
}
```
Response: `{ "ok": true, "logged": 2 }`

### `POST /api/sessions/{session_id}/intents`
**Purpose:** Log a single purchase-intent signal.

Request body:
```json
{
  "image_id": "abc123",
  "intent_type": "will_buy",
  "reason": ""
}
```
Response: `{ "ok": true }`

### `POST /api/sessions/{session_id}/orders`
**Purpose:** Save simulated order (phone + address).

Request body:
```json
{
  "phone": "0901234567",
  "address": "123 Nguyen Hue, Q1, Ho Chi Minh City"
}
```
Response: `{ "ok": true, "order_id": 42 }`

### `GET /api/analytics/behaviour-funnel`
**Purpose:** Full funnel stats — protected by `X-Admin-Key`.

Response:
```json
{
  "sessions": [
    {
      "session_id": "...",
      "user_name": "Minh",
      "impressions": 12,
      "cart_adds": 4,
      "will_buy": 2,
      "not_for_me": 1,
      "cart_rate": 0.333,
      "intent_rate": 0.5,
      "precision_at_k": 0.167
    }
  ],
  "aggregate": {
    "total_sessions": 10,
    "avg_precision_at_k": 0.21
  }
}
```

---

## Flutter Changes

### 1. `chat_screen.dart` — Banner text update

`_buildTopBanner()` hardcoded strings:
- **Title**: `'Item saved! ✨'` → `'Added to your cart 🛍️'`
- **Subtitle**: `'Whenever you want to end...'` → `'Check the top‑right corner to see your picks!'`

`chat_provider.dart` — When `'products'` SSE fires (inside `_handleSseEvent`):
- Call `ApiService.logImpressions(sessionId, products)` as fire-and-forget

### 2. `cart_screen.dart` — Intent buttons + Order CTA

**Intent buttons** — added to `_CartCard`:
```
┌────────────────┐
│   [image]      │
│  Product name  │
│  ┌───┐  ┌───┐ │
│  │ ✓ │  │ ✗ │ │   ← 36×36 icon buttons
│  └───┘  └───┘ │
└────────────────┘
```
- `✓` = `Icons.thumb_up_outlined` → calls `POST /intents` with `will_buy`; on success fills with `Icons.thumb_up` (green)
- `✗` = `Icons.thumb_down_outlined` → calls `POST /intents` with `not_for_me`; on success fills with `Icons.thumb_down` (red-ish)
- Tapping `✗` optionally shows a 1-line `TextField` for a reason (can be skipped with "Skip")

**"Let's make the order" CTA** — added at the bottom of `CartScreen` (only visible when `cart.count > 0`):
```
[  📦 Let's make the order  ]   ← full-width ElevatedButton
```
Tapping opens `_OrderDialog`:
```
┌──────────────────────────────────┐
│  📦 Place Your Order             │
│                                  │
│  📱 Phone number                 │
│  ┌────────────────────────────┐  │
│  │ 0901 234 567               │  │
│  └────────────────────────────┘  │
│                                  │
│  🏠 Delivery address             │
│  ┌────────────────────────────┐  │
│  │ 123 Nguyen Hue...          │  │
│  └────────────────────────────┘  │
│                                  │
│  [Cancel]   [Confirm Order ✓]    │
└──────────────────────────────────┘
```

### 3. `api_service.dart` — New methods

```dart
// Log product impressions (fire-and-forget)
Future<void> logImpressions(String sessionId, List<Product> products);

// Log purchase intent
Future<void> logIntent(String sessionId, String imageId, String intentType, {String reason = ''});

// Place order
Future<int> placeOrder(String sessionId, String phone, String address);
```

---

## Precision@K Formula

```
K = total impressions in session
will_buy_count = items with intent_type = 'will_buy'

Precision@K = will_buy_count / K
```

This is computed server-side in the analytics endpoint, per session and aggregated.

---

## Data Flow: Full Funnel

```
Search results arrive (products SSE)
        │
        ▼
Flutter auto-POSTs impression batch ────────────────► product_impressions
        │
User taps [Add to Cart]
        │
Backend SSE 'selection_saved'
        │
CartProvider.reload() ─────────────────────────────► selected_items (existing)
        │
User opens CartScreen
        │
User taps [✓] or [✗] on a card ───────────────────► product_intents (new)
        │
User taps [Let's make the order]
        │
Fills phone + address → submit ────────────────────► user_orders (new)
```

---

## Decisions Made

| Question | Decision | Rationale |
|----------|----------|-----------|
| Intent buttons: chat vs cart? | CartScreen | Less noisy; user is already reviewing their picks |
| Impression logging: client vs server? | Client (Flutter, fire-and-forget) | Server already knows products but has no session context at SSE time to batch easily |
| "Left corner" or "right corner"? | Top-right corner | Cart icon is in AppBar `actions:` (right side) |
| Qualitative reason for reject? | Optional (skippable) | Reduces friction; enough signal from the `not_for_me` event alone |
| Payment? | No — simulated only | Thesis scope; avoids PCI/legal complexity |

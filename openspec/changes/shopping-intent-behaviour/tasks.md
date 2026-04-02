# Tasks: Shopping Intent & Behaviour Stress Test

> **Status:** 🟡 In Progress — Python BE complete (8/15), Flutter FE pending
> **Change:** `shopping-intent-behaviour`
> **Design:** `design.md` | **Insights:** `insights-strategy.md`
> **Order:** Python (BE) ALL tasks first → Flutter (FE) after

---

## Implementation Map

```
PYTHON (BE) — complete before touching Flutter
────────────────────────────────────────────────────────────────
[x] Task 1   memory.py    DB schema: 4 new tables + 2 new columns     ✓ DONE
[x] Task 2   memory.py    Helper functions (log_*, save_order, funnel) ✓ DONE
[x] Task 3   main.py      Pydantic models for new endpoints            ✓ DONE
[x] Task 4   main.py      POST /impressions  endpoint                  ✓ DONE
[x] Task 5   main.py      POST /clicks       endpoint                  ✓ DONE
[x] Task 6   main.py      POST /intents      endpoint                  ✓ DONE
[x] Task 7   main.py      POST /orders       endpoint (+ session end)  ✓ DONE
[x] Task 8   main.py      GET  /analytics/behaviour-funnel endpoint    ✓ DONE
────────────────────────────────────────────────────────────────
FLUTTER (FE) — only start after Tasks 1-8 are verified
────────────────────────────────────────────────────────────────
[ ] Task 9   api_service.dart        4 new API methods
[ ] Task 10  chat_provider.dart      auto-log impressions on SSE
[x] Task 11  product card (chat)     GestureDetector.onTap → logClick()
[x] Task 12  chat_screen.dart        Update cart banner text
[x] Task 13  cart_screen.dart        Intent buttons ✓/✗ per card
[x] Task 14  cart_screen.dart        "Let's make the order" CTA + dialog
────────────────────────────────────────────────────────────────
[ ] Task 15  End-to-end funnel verification
```


---

## ═══ PYTHON (BACKEND) ═══

---

## Task 1 — DB Schema: 3 new tables + 2 new columns on `user_sessions`

**Files:**
- Modify: `fashion_agent/agent/memory.py` — inside `init_memory_tables()`, append to `ddl` string

### 1a. Append to the `ddl` string (before closing `"""`):

```python
    -- ── Behaviour: products clicked (tap on card in chat) ─────────────
    CREATE TABLE IF NOT EXISTS product_clicks (
        id           BIGSERIAL PRIMARY KEY,
        session_id   TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        image_id     VARCHAR NOT NULL,
        position     INT NOT NULL DEFAULT 0,        -- 1-based card position (1-6)
        search_query TEXT NOT NULL DEFAULT '',
        clicked_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_clicks_session
        ON product_clicks(session_id, clicked_at);

    -- ── Behaviour: products shown per search result ────────────────────
    CREATE TABLE IF NOT EXISTS product_impressions (
        id           BIGSERIAL PRIMARY KEY,
        session_id   TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        image_id     VARCHAR NOT NULL,
        search_query TEXT NOT NULL DEFAULT '',
        position     INT NOT NULL DEFAULT 0,
        shown_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_impressions_session
        ON product_impressions(session_id, shown_at);

    -- ── Behaviour: purchase intent signals ────────────────────────────
    CREATE TABLE IF NOT EXISTS product_intents (
        id            BIGSERIAL PRIMARY KEY,
        session_id    TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        image_id      VARCHAR NOT NULL,
        intent_type   TEXT NOT NULL CHECK (intent_type IN ('will_buy', 'not_for_me')),
        reason        TEXT NOT NULL DEFAULT '',
        logged_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (session_id, image_id, intent_type)
    );

    CREATE INDEX IF NOT EXISTS idx_intents_session
        ON product_intents(session_id, logged_at);

    -- ── Checkout: simulated order (phone + address) ───────────────────
    CREATE TABLE IF NOT EXISTS user_orders (
        id          SERIAL PRIMARY KEY,
        session_id  TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        phone       TEXT NOT NULL DEFAULT '',
        address     TEXT NOT NULL DEFAULT '',
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_orders_session
        ON user_orders(session_id);

    -- ── Session lifecycle: when and how session ended ─────────────────
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ;
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS ended_by TEXT
            CHECK (ended_by IN ('order', 'rating', 'timeout'));
```

**Verify:** Restart backend → `init_memory_tables()` runs on startup.  
Check: `SELECT column_name FROM information_schema.columns WHERE table_name = 'user_sessions';` — should include `ended_at` and `ended_by`.  
Check: `\dt` in psql → shows `product_clicks`, `product_impressions`, `product_intents`, `user_orders`.

---

## Task 2 — Helper functions in `memory.py`

**Files:**
- Modify: `fashion_agent/agent/memory.py` — add these functions at the bottom of the file

```python
# ── Behaviour tracking helpers ─────────────────────────────────────────────


def log_impression_batch(session_id: str, items: list[dict]) -> int:
    """Batch-insert product impressions. Each item: {image_id, search_query, position}."""
    if not items:
        return 0
    inserted = 0
    with _db_conn() as conn:
        with conn.cursor() as cur:
            for item in items:
                cur.execute(
                    """
                    INSERT INTO product_impressions
                        (session_id, image_id, search_query, position)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        session_id,
                        item.get("image_id", ""),
                        item.get("search_query", ""),
                        item.get("position", 0),
                    ),
                )
                inserted += 1
        conn.commit()
    return inserted


def log_click(
    session_id: str,
    image_id: str,
    position: int,
    search_query: str = "",
) -> None:
    """Log a product card tap (click event)."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO product_clicks
                    (session_id, image_id, position, search_query)
                VALUES (%s, %s, %s, %s);
                """,
                (session_id, image_id, position, search_query),
            )
        conn.commit()


def log_intent(
    session_id: str,
    image_id: str,
    intent_type: str,
    reason: str = "",
) -> None:
    """Log a purchase intent signal ('will_buy' | 'not_for_me'). Idempotent."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO product_intents
                    (session_id, image_id, intent_type, reason)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (session_id, image_id, intent_type) DO NOTHING;
                """,
                (session_id, image_id, intent_type, reason),
            )
        conn.commit()


def save_order(session_id: str, phone: str, address: str) -> int:
    """Save a simulated order and mark the session as ended. Returns order id."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_orders (session_id, phone, address)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (session_id, phone, address),
            )
            order_id = cur.fetchone()[0]
            # Mark session as ended by order
            cur.execute(
                """
                UPDATE user_sessions
                SET ended_at = NOW(), ended_by = 'order'
                WHERE session_id = %s;
                """,
                (session_id,),
            )
        conn.commit()
    return order_id


def get_session_funnel(session_id: str) -> dict:
    """Return full funnel stats for one session."""
    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT COUNT(*) FROM product_impressions WHERE session_id = %s",
                (session_id,),
            )
            impressions = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM product_clicks WHERE session_id = %s",
                (session_id,),
            )
            clicks = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM selected_items WHERE session_id = %s",
                (session_id,),
            )
            cart_adds = cur.fetchone()[0]

            cur.execute(
                """
                SELECT intent_type, COUNT(*) AS cnt
                FROM product_intents
                WHERE session_id = %s
                GROUP BY intent_type;
                """,
                (session_id,),
            )
            intents = {row["intent_type"]: row["cnt"] for row in cur.fetchall()}

            cur.execute(
                "SELECT COUNT(*) FROM user_orders WHERE session_id = %s",
                (session_id,),
            )
            converted = cur.fetchone()[0] > 0

            # Token data from existing VIEW
            cur.execute(
                "SELECT model_name, total_tokens FROM session_token_summary WHERE session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            model_name = row["model_name"] if row else ""
            total_tokens = row["total_tokens"] if row else 0

    will_buy = intents.get("will_buy", 0)
    not_for_me = intents.get("not_for_me", 0)

    return {
        "session_id": session_id,
        "model_name": model_name,
        "total_tokens": total_tokens,
        "impressions": impressions,
        "clicks": clicks,
        "cart_adds": cart_adds,
        "will_buy": will_buy,
        "not_for_me": not_for_me,
        "converted": converted,
        "ctr": round(clicks / impressions, 3) if impressions else 0.0,
        "cart_rate": round(cart_adds / clicks, 3) if clicks else 0.0,
        "intent_rate": round(will_buy / cart_adds, 3) if cart_adds else 0.0,
        "precision_at_k": round(will_buy / impressions, 3) if impressions else 0.0,
    }
```

**Verify:** Open a Python shell in the project:
```bash
cd fashion_agent
uv run python -c "from agent.memory import log_click; print('ok')"
```
Expected: `ok` with no import errors.

---

## Task 3 — `main.py`: New Pydantic request models

**Files:**
- Modify: `fashion_agent/api/main.py` — add models after the existing `DemographicsResponse` block (around line 143)

```python
# ── Behaviour tracking models ──────────────────────────────────────────────

class ImpressionItem(BaseModel):
    image_id: str
    search_query: str = ""
    position: int = 0


class LogImpressionsRequest(BaseModel):
    items: list[ImpressionItem]


class ClickRequest(BaseModel):
    image_id: str
    position: int = 0
    search_query: str = ""


class IntentRequest(BaseModel):
    image_id: str
    intent_type: str   # "will_buy" | "not_for_me"
    reason: str = ""


class OrderRequest(BaseModel):
    phone: str
    address: str
```

**Verify:** `uv run python -c "from api.main import LogImpressionsRequest; print('ok')`

---

## Task 4 — `main.py`: `POST /api/sessions/{id}/impressions`

**Files:**
- Modify: `fashion_agent/api/main.py` — add after the `/api/sessions/{session_id}/selections` route

```python
@app.post("/api/sessions/{session_id}/impressions")
async def log_impressions_endpoint(session_id: str, req: LogImpressionsRequest):
    """Batch-log product impressions for a search result."""
    from agent.memory import log_impression_batch
    try:
        logged = log_impression_batch(
            session_id,
            [
                {
                    "image_id": i.image_id,
                    "search_query": i.search_query,
                    "position": i.position,
                }
                for i in req.items
            ],
        )
        return {"ok": True, "logged": logged}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

**Verify:**
```bash
curl -s -X POST http://localhost:8000/api/sessions/<SESSION_ID>/impressions \
  -H "Content-Type: application/json" \
  -d '{"items":[{"image_id":"test_img","search_query":"white shirt","position":1}]}'
```
Expected: `{"ok":true,"logged":1}`

---

## Task 5 — `main.py`: `POST /api/sessions/{id}/clicks`

**Files:**
- Modify: `fashion_agent/api/main.py` — add after impressions endpoint

```python
@app.post("/api/sessions/{session_id}/clicks")
async def log_click_endpoint(session_id: str, req: ClickRequest):
    """Log a product card tap (click event)."""
    from agent.memory import log_click
    try:
        log_click(
            session_id,
            req.image_id,
            req.position,
            req.search_query,
        )
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

**Verify:**
```bash
curl -s -X POST http://localhost:8000/api/sessions/<SESSION_ID>/clicks \
  -H "Content-Type: application/json" \
  -d '{"image_id":"test_img","position":2,"search_query":"white shirt"}'
```
Expected: `{"ok":true}`  
Check DB: `SELECT * FROM product_clicks LIMIT 5;` — row should appear.

---

## Task 6 — `main.py`: `POST /api/sessions/{id}/intents`

**Files:**
- Modify: `fashion_agent/api/main.py` — add after clicks endpoint

```python
@app.post("/api/sessions/{session_id}/intents")
async def log_intent_endpoint(session_id: str, req: IntentRequest):
    """Log a purchase intent signal (will_buy | not_for_me)."""
    if req.intent_type not in ("will_buy", "not_for_me"):
        raise HTTPException(
            status_code=400,
            detail="intent_type must be 'will_buy' or 'not_for_me'",
        )
    from agent.memory import log_intent
    try:
        log_intent(session_id, req.image_id, req.intent_type, req.reason)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

**Verify:**
```bash
curl -s -X POST http://localhost:8000/api/sessions/<SESSION_ID>/intents \
  -H "Content-Type: application/json" \
  -d '{"image_id":"test_img","intent_type":"will_buy","reason":""}'
```
Expected: `{"ok":true}`

---

## Task 7 — `main.py`: `POST /api/sessions/{id}/orders` (also ends session)

**Files:**
- Modify: `fashion_agent/api/main.py` — add after intents endpoint

```python
@app.post("/api/sessions/{session_id}/orders")
async def place_order_endpoint(session_id: str, req: OrderRequest):
    """
    Save a simulated order (phone + address) and mark session as ended.
    This is the conversion event — CR is computed from sessions with an order.
    """
    if not req.phone.strip():
        raise HTTPException(status_code=400, detail="phone is required")
    if not req.address.strip():
        raise HTTPException(status_code=400, detail="address is required")
    from agent.memory import save_order
    try:
        order_id = save_order(session_id, req.phone.strip(), req.address.strip())
        return {"ok": True, "order_id": order_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

**Verify:**
```bash
curl -s -X POST http://localhost:8000/api/sessions/<SESSION_ID>/orders \
  -H "Content-Type: application/json" \
  -d '{"phone":"0901234567","address":"123 Nguyen Hue, Q1, HCM"}'
```
Expected: `{"ok":true,"order_id":1}`  
Check DB: `SELECT ended_at, ended_by FROM user_sessions WHERE session_id = '<ID>';` — both should be non-null.

---

## Task 8 — `main.py`: `GET /api/analytics/behaviour-funnel`

**Files:**
- Modify: `fashion_agent/api/main.py` — add after orders endpoint

```python
@app.get("/api/analytics/behaviour-funnel")
async def get_behaviour_funnel_endpoint(request: Request):
    """
    Full funnel analytics including per-session metrics and model comparison.
    Protected by X-Admin-Key header.

    Returns:
        sessions: per-session funnel (impressions, clicks, cart, intent, CR, P@K)
        model_comparison: aggregate stats grouped by LLM model
        aggregate: overall totals
    """
    admin_key = os.getenv("ADMIN_SECRET_KEY", "")
    if not admin_key:
        raise HTTPException(status_code=503, detail="Analytics not configured (ADMIN_SECRET_KEY missing)")
    if request.headers.get("X-Admin-Key", "") != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    from agent.memory import get_session_funnel
    import psycopg2
    from psycopg2.extras import DictCursor

    try:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=5,
        )
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT s.session_id, s.user_name, s.gender,
                       DATE_PART('year', NOW()) - s.year_of_birth AS age
                FROM user_sessions s
                ORDER BY s.created_at DESC
                LIMIT 500;
                """
            )
            rows = cur.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            funnel = get_session_funnel(row["session_id"])
            funnel["user_name"] = row["user_name"]
            funnel["gender"] = row["gender"]
            funnel["age"] = row["age"]
            sessions.append(funnel)

        # Model comparison aggregate
        from collections import defaultdict
        model_groups: dict = defaultdict(lambda: {
            "sessions": 0, "orders": 0, "total_tokens": 0,
            "precision_sum": 0.0,
        })
        for s in sessions:
            model = s["model_name"] or "unknown"
            model_groups[model]["sessions"] += 1
            model_groups[model]["orders"] += 1 if s["converted"] else 0
            model_groups[model]["total_tokens"] += s["total_tokens"] or 0
            model_groups[model]["precision_sum"] += s["precision_at_k"]

        model_comparison = []
        for model, g in model_groups.items():
            n = g["sessions"]
            model_comparison.append({
                "model": model,
                "sessions": n,
                "orders": g["orders"],
                "conversion_rate": round(g["orders"] / n, 3) if n else 0.0,
                "avg_precision_at_k": round(g["precision_sum"] / n, 3) if n else 0.0,
                "avg_tokens": round(g["total_tokens"] / n) if n else 0,
            })

        total = len(sessions)
        converted = sum(1 for s in sessions if s["converted"])

        return {
            "sessions": sessions,
            "model_comparison": sorted(model_comparison, key=lambda x: -x["conversion_rate"]),
            "aggregate": {
                "total_sessions": total,
                "converted_sessions": converted,
                "overall_cr": round(converted / total, 3) if total else 0.0,
                "avg_precision_at_k": round(
                    sum(s["precision_at_k"] for s in sessions) / total, 3
                ) if total else 0.0,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

**Verify:**
```bash
curl -s -H "X-Admin-Key: <your-ADMIN_SECRET_KEY>" \
  http://localhost:8000/api/analytics/behaviour-funnel | python3 -m json.tool
```
Expected: JSON with `sessions`, `model_comparison`, `aggregate` keys.

---

## ═══ FLUTTER (FRONTEND) ═══

> **Start here only after Tasks 1–8 are verified working.**

---

## Task 9 — `api_service.dart`: 4 new API methods

**Files:**
- Modify: `clothie_web/lib/services/api_service.dart`

Add at the bottom of the `ApiService` class (before the closing `}`):

```dart
/// Batch-log product impressions (fire-and-forget — errors are swallowed).
Future<void> logImpressions(
  String sessionId,
  List<Map<String, dynamic>> items,
) async {
  try {
    await _client.post(
      Uri.parse('$_base/api/sessions/$sessionId/impressions'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'items': items}),
    );
  } catch (_) {
    // Analytics errors must never disrupt chat
  }
}

/// Log a product card tap event (fire-and-forget).
Future<void> logClick(
  String sessionId,
  String imageId,
  int position, {
  String searchQuery = '',
}) async {
  try {
    await _client.post(
      Uri.parse('$_base/api/sessions/$sessionId/clicks'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'image_id': imageId,
        'position': position,
        'search_query': searchQuery,
      }),
    );
  } catch (_) {
    // Fire-and-forget
  }
}

/// Log a purchase intent signal.
Future<void> logIntent(
  String sessionId,
  String imageId,
  String intentType, {
  String reason = '',
}) async {
  await _client.post(
    Uri.parse('$_base/api/sessions/$sessionId/intents'),
    headers: {'Content-Type': 'application/json'},
    body: json.encode({
      'image_id': imageId,
      'intent_type': intentType,
      'reason': reason,
    }),
  );
}

/// Place a simulated order. Returns the new order ID.
Future<int> placeOrder(
  String sessionId,
  String phone,
  String address,
) async {
  final resp = await _client.post(
    Uri.parse('$_base/api/sessions/$sessionId/orders'),
    headers: {'Content-Type': 'application/json'},
    body: json.encode({'phone': phone, 'address': address}),
  );
  if (resp.statusCode != 200) {
    throw Exception('Order failed: ${resp.body}');
  }
  return (json.decode(resp.body) as Map<String, dynamic>)['order_id'] as int;
}
```

**Verify:**
```bash
cd clothie_web && flutter analyze lib/services/api_service.dart
```
Expected: No analysis issues.

---

## Task 10 — `chat_provider.dart`: Auto-log impressions on `products` SSE

**Files:**
- Modify: `clothie_web/lib/providers/chat_provider.dart`

### 10a. Add `_sessionId` field and setter:

```dart
String _sessionId = '';

void setSessionId(String id) {
  _sessionId = id;
}
```

### 10b. In `_handleSseEvent`, find the `'products'` case and add impression logging after building `aiMsg.products`:

```dart
case 'products':
  // ... existing product parsing code ...

  // ── Auto-log impressions (fire-and-forget) ──────────────────
  if (_sessionId.isNotEmpty && aiMsg.products.isNotEmpty) {
    final impressionItems = aiMsg.products.asMap().entries.map((e) => {
      'image_id': e.value.imageId,
      'search_query': '',          // search query not in SSE payload
      'position': e.key + 1,       // 1-based rank
    }).toList();
    _api.logImpressions(_sessionId, impressionItems); // fire-and-forget
  }
```

### 10c. In `chat_screen.dart`, pass `sessionId` to provider after creation:

In the `ChangeNotifierProxyProvider` `create:` callback:
```dart
create: (ctx) {
  final provider = ChatProvider(
    onSelectionSaved: ctx.read<CartProvider>().onSelectionSaved,
  );
  provider.setSessionId(widget.sessionId);
  return provider;
},
```

**Verify:** Search for "white shirt" → check DB:
```sql
SELECT COUNT(*) FROM product_impressions;
```
Count should increase after each search.

---

## Task 11 — Product card in chat: `GestureDetector.onTap` → `logClick()`

**Files:**
- Modify: wherever the product card widget is defined inside chat message rendering

Find the product card widget (look for `image_id`, `GestureDetector`, or `InkWell` in the chat bubble rendering code). Wrap the card with `GestureDetector` if not already wrapped, and add:

```dart
GestureDetector(
  onTap: () {
    // Log click — fire-and-forget
    ApiService().logClick(
      sessionId,                         // pass from parent
      product.imageId,
      productIndex + 1,                  // 1-based position
    );
    // Optionally: open product detail dialog/sheet here
  },
  child: /* existing card widget */,
),
```

Pass `sessionId` down from `ChatScreen` → chat message widget → product card widget as a constructor parameter.

**Verify:** Tap a product card → check DB:
```sql
SELECT image_id, position, clicked_at FROM product_clicks ORDER BY clicked_at DESC LIMIT 5;
```

---

## Task 12 — `chat_screen.dart`: Update cart banner text

**Files:**
- Modify: `clothie_web/lib/screens/chat_screen.dart`

Find `_buildTopBanner()`. Replace the two hardcoded text strings:

```dart
// BEFORE:
Text('Item saved! ✨', ...)
Text('Whenever you want to end, press the button and vote for me. Love you 💕', ...)

// AFTER:
Text('Added to your cart 🛍️', ...)
Text('Check the top‑right corner to see all your picks!', ...)
```

**Verify:** Confirm an item in chat → slide-down banner shows new text.

---

## Task 13 — `cart_screen.dart`: Intent buttons ✓/✗ per card

**Files:**
- Modify: `clothie_web/lib/screens/cart_screen.dart`

### 13a. Convert `_CartCard` to `StatefulWidget`:

```dart
class _CartCard extends StatefulWidget {
  final CartItem item;
  final String sessionId;
  const _CartCard({required this.item, required this.sessionId});

  @override
  State<_CartCard> createState() => _CartCardState();
}

class _CartCardState extends State<_CartCard> {
  String? _intentLogged;   // null | 'will_buy' | 'not_for_me'
  bool _sending = false;

  Future<void> _logIntent(String type) async {
    if (_sending || _intentLogged != null) return;
    setState(() => _sending = true);
    try {
      await ApiService().logIntent(widget.sessionId, widget.item.imageId, type);
      setState(() => _intentLogged = type);
    } catch (_) {
      // Best-effort — silently fail
    } finally {
      setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      // ... existing card structure ...
      child: Column(
        children: [
          // ... existing image / label / color widgets ...

          // ── Intent buttons ────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                iconSize: 20,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                icon: Icon(
                  _intentLogged == 'will_buy'
                      ? Icons.thumb_up
                      : Icons.thumb_up_outlined,
                  color: _intentLogged == 'will_buy'
                      ? Colors.green
                      : theme.colorScheme.onSurface.withOpacity(0.5),
                  size: 18,
                ),
                tooltip: "I'll buy this",
                onPressed: _sending ? null : () => _logIntent('will_buy'),
              ),
              const SizedBox(width: 4),
              IconButton(
                iconSize: 20,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                icon: Icon(
                  _intentLogged == 'not_for_me'
                      ? Icons.thumb_down
                      : Icons.thumb_down_outlined,
                  color: _intentLogged == 'not_for_me'
                      ? theme.colorScheme.error
                      : theme.colorScheme.onSurface.withOpacity(0.5),
                  size: 18,
                ),
                tooltip: 'Not for me',
                onPressed: _sending ? null : () => _logIntent('not_for_me'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
```

### 13b. Pass `sessionId` to `_CartCard` in `GridView.builder`:

```dart
itemBuilder: (_, i) => _CartCard(
  item: cart.items[i],
  sessionId: sessionId,   // pass from CartScreen
),
```

**Note:** `CartScreen` needs `sessionId` — add it as a constructor field (see Task 14).

**Verify:** Open CartScreen → intent buttons appear on cards. Tap ✓ → icon turns green.  
Check DB: `SELECT * FROM product_intents;`

---

## Task 14 — `cart_screen.dart`: "Let's make the order" CTA + dialog

**Files:**
- Modify: `clothie_web/lib/screens/cart_screen.dart`

### 14a. Add `sessionId` field to `CartScreen` and update `show()`:

```dart
class CartScreen extends StatelessWidget {
  final String sessionId;
  const CartScreen({super.key, required this.sessionId});

  static Future<void> show(BuildContext context, String sessionId) {
    context.read<CartProvider>().reload();
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider.value(
        value: context.read<CartProvider>(),
        child: CartScreen(sessionId: sessionId),
      ),
    );
  }
```

Update the call site in `chat_screen.dart` `_buildAppBar`:
```dart
onPressed: () => CartScreen.show(ctx, widget.sessionId),
```

### 14b. Add "Let's make the order" button at the bottom of `CartScreen.build`:

After the `Expanded` scrollable area, inside the `Column`:
```dart
Consumer<CartProvider>(
  builder: (_, cart, __) {
    if (cart.count == 0) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          icon: const Text('📦'),
          label: Text(
            "Let's make the order",
            style: GoogleFonts.outfit(fontWeight: FontWeight.w600),
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: theme.colorScheme.primary,
            foregroundColor: theme.colorScheme.onPrimary,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
          onPressed: () => _showOrderDialog(context, sessionId),
        ),
      ),
    );
  },
),
```

### 14c. Implement `_showOrderDialog`:

```dart
void _showOrderDialog(BuildContext context, String sessionId) {
  final phoneCtrl = TextEditingController();
  final addressCtrl = TextEditingController();
  final theme = Theme.of(context);

  showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(
        '📦 Place Your Order',
        style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: phoneCtrl,
            keyboardType: TextInputType.phone,
            decoration: InputDecoration(
              labelText: '📱 Phone number',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: addressCtrl,
            maxLines: 2,
            decoration: InputDecoration(
              labelText: '🏠 Delivery address',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () async {
            final phone = phoneCtrl.text.trim();
            final address = addressCtrl.text.trim();
            if (phone.isEmpty || address.isEmpty) return;
            try {
              await ApiService().placeOrder(sessionId, phone, address);
              if (ctx.mounted) Navigator.pop(ctx);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text("🎉 Order placed! We'll be in touch."),
                  ),
                );
              }
            } catch (e) {
              if (ctx.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Error: $e')),
                );
              }
            }
          },
          child: Text('Confirm Order ✓', style: GoogleFonts.outfit()),
        ),
      ],
    ),
  );
}
```

**Verify:**
1. Open CartScreen with ≥1 item → "Let's make the order" button visible at bottom
2. Tap → dialog opens with phone + address fields
3. Fill in and submit → snackbar appears
4. Check DB: `SELECT phone, address, created_at FROM user_orders;`
5. Check session end: `SELECT ended_at, ended_by FROM user_sessions WHERE session_id = '<ID>';`

---

## Task 15 — End-to-End Funnel Verification

Run through the **complete user journey** and verify every table is populated:

| Step | Action | DB check |
|---|---|---|
| 1 | Start chat session | `SELECT * FROM user_sessions ORDER BY created_at DESC LIMIT 1;` |
| 2 | Search for a product | `SELECT COUNT(*) FROM product_impressions;` — increments |
| 3 | Tap a product card | `SELECT COUNT(*) FROM product_clicks;` — increments |
| 4 | Say "1" + confirm "yes" | `SELECT COUNT(*) FROM selected_items;` — increments |
| 5 | Open CartScreen → tap ✓ | `SELECT * FROM product_intents;` — row with `will_buy` |
| 6 | Tap "Let's make the order" → submit | `SELECT * FROM user_orders;` — row appears |
| 7 | Check session ended | `SELECT ended_at, ended_by FROM user_sessions WHERE ...;` — both non-null |
| 8 | Hit analytics endpoint | `curl -H "X-Admin-Key: ..." http://localhost:8000/api/analytics/behaviour-funnel` |
| 9 | Verify funnel metrics | Response shows `ctr`, `cart_rate`, `intent_rate`, `precision_at_k`, `converted: true` |

---

## Summary

| Layer | Files Changed | New Capabilities |
|---|---|---|
| DB | `memory.py` | `product_impressions`, `product_clicks`, `product_intents`, `user_orders` tables; `ended_at`/`ended_by` on sessions |
| BE | `memory.py` | `log_impression_batch`, `log_click`, `log_intent`, `save_order`, `get_session_funnel` |
| BE | `main.py` | 5 new endpoints (impressions, clicks, intents, orders, analytics) |
| FE | `api_service.dart` | `logImpressions`, `logClick`, `logIntent`, `placeOrder` |
| FE | `chat_provider.dart` | Auto-impression on SSE |
| FE | Chat product card | Tap → logClick |
| FE | `chat_screen.dart` | Banner text update |
| FE | `cart_screen.dart` | Intent buttons + Order CTA + dialog |

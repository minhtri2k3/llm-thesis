# Tasks: Clothie Web Frontend

## Phase 1 — Backend Additions (fashion_agent)

### Task 1.1: Update DB schema in memory.py
**File**: `fashion_agent/agent/memory.py`
- In `init_memory_tables()`, add two SQL blocks after the existing DDL:
  ```sql
  ALTER TABLE user_sessions
      ADD COLUMN IF NOT EXISTS user_name TEXT NOT NULL DEFAULT '';

  CREATE TABLE IF NOT EXISTS user_ratings (
      id          SERIAL PRIMARY KEY,
      session_id  TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
      user_name   TEXT NOT NULL DEFAULT '',
      rating      INT  NOT NULL CHECK (rating BETWEEN 1 AND 10),
      feedback    TEXT NOT NULL DEFAULT '',
      created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );
  CREATE INDEX IF NOT EXISTS idx_user_ratings_session
      ON user_ratings(session_id);
  ```
- Also update `create_session()` to accept optional `user_name: str = ""` parameter and store it

### Task 1.2: Add POST /api/sessions endpoint
**File**: `fashion_agent/api/main.py`
- Add `CreateSessionRequest(BaseModel)` with `user_name: str = ""`
- Add `CreateSessionResponse(BaseModel)` with `session_id: str`
- Add `@app.post("/api/sessions")` handler that calls `create_session(user_name)` and returns the ID

### Task 1.3: Add POST /api/rating endpoint
**File**: `fashion_agent/api/main.py`
- Add `RatingRequest(BaseModel)` with `session_id`, `rating: int`, `feedback: str`
- Add `RatingResponse(BaseModel)` with `ok: bool`
- Add `@app.post("/api/rating")` handler that inserts into `user_ratings` via `_db_conn()`
- Validate rating is between 1 and 10 (raise 400 if not)

### Task 1.4: Update docker-compose.yml
**File**: `fashion_agent/docker-compose.yml`
- **Remove** the existing `cloudflared` service block entirely
- **Add** `clothie-web` service:
  - `build: context: ../clothie_web`
  - networks: `internal`
  - ports: `"3000:80"`
  - depends_on: `fashion-api`
- **Add** `cloudflared-fe` service:
  - `image: cloudflare/cloudflared:latest`
  - `command: tunnel run`
  - `environment: TUNNEL_TOKEN: ${CF_FE_TUNNEL_TOKEN}`
  - networks: `internal`
  - depends_on: `clothie-web`
- **Add** `CF_FE_TUNNEL_TOKEN` to `.env.example` with comment

---

## Phase 2 — Flutter Project Setup

### Task 2.1: Create Flutter web project
**Location**: `/Users/tringuyen/llm-thesis/clothie_web/`
```bash
cd /Users/tringuyen/llm-thesis
flutter create clothie_web --platforms web
```

### Task 2.2: Update pubspec.yaml
**File**: `clothie_web/pubspec.yaml`
- Add dependencies:
  - `http: ^1.2.0`
  - `provider: ^6.1.0`
  - `google_fonts: ^6.2.0`
- Remove unused Flutter default dependencies

### Task 2.3: Create config.dart
**File**: `clothie_web/lib/config.dart`
- `const String kApiBaseUrl = '';`  (empty string = relative URL)
- `const int kSplashDurationSeconds = 2;`
- `const int kMaxStarRating = 10;`

---

## Phase 3 — Models & Services

### Task 3.1: Create ChatMessage model
**File**: `clothie_web/lib/models/chat_message.dart`
- `enum MessageRole { user, assistant }`
- `enum MessageStatus { done, streaming, thinking }`
- `class ChatMessage`:
  - `id`, `role`, `content`, `status`
  - `List<ThinkingStep> thinkingSteps`
  - `List<Product> products`
  - `String? stylingTip`

### Task 3.2: Create Product model
**File**: `clothie_web/lib/models/product.dart`
- `class Product` with `imageId`, `imageUrl`, `label`, `color`, `caption`, `score`
- `factory Product.fromJson(Map<String, dynamic> json)` parsing `/api/images/{filename}` for image URL

### Task 3.3: Create ApiService
**File**: `clothie_web/lib/services/api_service.dart`
- `createSession(String userName) → Future<String>` — POST /api/sessions
- `chatStream(String message, String sessionId) → Stream<SseEvent>` — POST /api/chat/stream
  - Parse SSE format: event type + data JSON, yield `SseEvent` objects on empty-line boundary
- `submitRating(String sessionId, int rating, String feedback) → Future<void>` — POST /api/rating
- `SseEvent` class with `type` and `data` fields

### Task 3.4: Create ChatProvider (state management)
**File**: `clothie_web/lib/providers/chat_provider.dart`
- Extends `ChangeNotifier`
- Holds: `messages`, `isLoading`, `thinkingSteps`, `currentThinkingStatus`
- `sendMessage(String text)` method: adds user message, streams AI response, updates state per SSE event
- `resetChat()` method for new sessions

---

## Phase 4 — Shared Widgets

### Task 4.1: FlyingIconBackground widget
**File**: `clothie_web/lib/widgets/flying_icon_bg.dart`
- Uses `AnimationController` with `repeat(reverse: false)`
- Spawns 12-15 floating `👗` emoji icons at random positions
- Each icon has independent: x/y velocity, speed, opacity, size (20-40px)
- Uses `CustomPainter` or stacked `Positioned` widgets inside a `Stack`
- Infinite loop animation — icons reappear from opposite edge when they leave screen

### Task 4.2: ChatBubble widget
**File**: `clothie_web/lib/widgets/chat_bubble.dart`
- `UserBubble`: right-aligned, deep purple/indigo gradient, white text, rounded corners
- `AssistantBubble`: left-aligned, dark surface card, light text
- Handles `MessageStatus.streaming` with cursor blink effect
- Handles `MessageStatus.thinking` by showing `ThinkingIndicator`
- Shows `ProductCard` list below text if `message.products` is not empty
- Shows `stylingTip` in italic below message if present

### Task 4.3: ThinkingIndicator widget
**File**: `clothie_web/lib/widgets/thinking_indicator.dart`
- Animated 3-dot pulse (like iMessage typing indicator)
- Shows "Thinking..." text with subtle fade
- Displays progressive thinking steps as they arrive with check icons
- Collapses to "Thought for Xs ✓" when `thinking_end` arrives

### Task 4.4: ProductCard widget
**File**: `clothie_web/lib/widgets/product_card.dart`
- Horizontal scrollable row of product cards
- Each card: image from `/api/images/{filename}`, label, color, caption
- Rounded corners, subtle shadow
- Fallback placeholder icon if image fails to load

### Task 4.5: StarRating widget
**File**: `clothie_web/lib/widgets/star_rating.dart`
- Row of 10 star/circle widgets
- Tap to select — fills stars 1 through selected
- Selected star: filled gold ⭐, unselected: outline
- Animated scale on tap

---

## Phase 5 — Screens

### Task 5.1: SplashScreen
**File**: `clothie_web/lib/screens/splash_screen.dart`
- Full-screen dark gradient background
- `FlyingIconBackground` widget filling entire screen
- Center: app logo "Clothie" in large Google Font (Outfit/Inter)
- Subtitle: "AI Fashion Assistant"
- After `kSplashDurationSeconds`: `Navigator.pushReplacement` to `RegisterScreen`

### Task 5.2: RegisterScreen
**File**: `clothie_web/lib/screens/register_screen.dart`
- `FlyingIconBackground` as background layer
- Center card (glassmorphism style: blur + semi-transparent):
  - "Welcome to Clothie" title
  - "Tell us your name to get started" subtitle
  - `TextField` with placeholder "Enter your name"
  - Primary action button "Start Chatting →"
- On button tap:
  - Validate name not empty
  - Show loading indicator
  - Call `apiService.createSession(name)` → get `session_id`
  - Navigate to `ChatScreen(sessionId, userName)`

### Task 5.3: ChatScreen
**File**: `clothie_web/lib/screens/chat_screen.dart`
- Dark background (no flying icons — focus on chat)
- AppBar: "Clothie 👗" title + "End Session" action button
- `ListView.builder` for messages — auto-scrolls to bottom
- Each item: `ChatBubble` (UserBubble or AssistantBubble based on role)
- Bottom input row:
  - `TextField` (placeholder: "Ask about fashion...")
  - Send button (disabled while `isLoading`)
- On send: call `chatProvider.sendMessage(text)`
- "End Session" button navigates to `RatingScreen`
- Handle SSE events via `ChatProvider`:
  - thinking_start → add thinking bubble
  - thinking_step → update thinking steps
  - thinking_end → collapse thinking block
  - token → append to streaming bubble
  - products → attach products to current AI message
  - done → finalize message

### Task 5.4: RatingScreen
**File**: `clothie_web/lib/screens/rating_screen.dart`
- Dark background with subtle gradient
- Header: "How was your experience?"
- Section 1: `StarRating` widget (1-10), currently selected count shown as "X/10"
- Section 2: `TextField` multiline (placeholder: "What do you think about this system?", max 4 lines)
- "Submit Feedback" button:
  - Validate: star rating selected + feedback not empty
  - Call `apiService.submitRating(sessionId, rating, feedback)`
  - Show success snackbar "Thank you! 🙏"
  - After 1.5s: `Navigator.pushAndRemoveUntil` back to `SplashScreen` (reset everything)

---

## Phase 6 — Docker Setup

### Task 6.1: Create nginx.conf
**File**: `clothie_web/nginx.conf`
- Server block on port 80
- `location /`: `try_files $uri $uri/ /index.html`
- `location /api/`: proxy_pass + SSE headers (`proxy_buffering off`, `proxy_read_timeout 3600s`, etc.)

### Task 6.2: Create Dockerfile
**File**: `clothie_web/Dockerfile`
- Stage 1: `FROM ghcr.io/cirruslabs/flutter:stable as builder`
  - `flutter pub get`
  - `flutter build web --release`
- Stage 2: `FROM nginx:alpine`
  - Copy `build/web` → `/usr/share/nginx/html`
  - Copy `nginx.conf`
  - `EXPOSE 80`

### Task 6.3: Add CF_FE_TUNNEL_TOKEN to .env
**File**: `fashion_agent/.env`
- Add `CF_FE_TUNNEL_TOKEN=eyJhIjoiOGEzZDA5...` (the token from explore session)
**File**: `fashion_agent/.env.example`
- Add `CF_FE_TUNNEL_TOKEN=<your-cloudflare-fe-tunnel-token>`

---

## Phase 7 — Verification

### Task 7.1: Test BE endpoints
```bash
# Test session creation
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_name": "Test User"}'

# Test rating
curl -X POST http://localhost:8000/api/rating \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<id>", "rating": 8, "feedback": "Great system!"}'
```

### Task 7.2: Test Flutter locally
```bash
cd clothie_web
flutter run -d chrome
```
- Verify all 4 screens render
- Verify SSE streaming works (tokens appear progressively)
- Verify thinking indicator animates and collapses

### Task 7.3: Build and test Docker
```bash
cd fashion_agent
docker compose build clothie-web
docker compose up -d clothie-web
# Open http://localhost:3000 — should see the Flutter app
# Test /api/ proxy: http://localhost:3000/api/health
```

### Task 7.4: Full stack test
```bash
cd fashion_agent
docker compose up -d
# Verify cloudflared-fe starts and connects
# Open public Cloudflare URL — full session test
```

---

## Dependency Order

```
Task 1.1 ─► Task 1.2 ─► Task 1.4
         └► Task 1.3 ─►

Task 2.1 ─► Task 2.2 ─► Task 2.3
                      ─► Task 3.1 ─► Task 3.3 ─► Task 3.4
                      ─► Task 3.2 ─►
                      ─► Task 4.1
                      ─► Task 4.2 (needs 4.3, 4.4)
                      ─► Task 5.1 ─► Task 5.2 ─► Task 5.3 ─► Task 5.4
                      ─► Task 6.1 ─► Task 6.2

All Phase 1-6 tasks ─► Phase 7 (verification)
```

## Total Estimated Tasks: 23

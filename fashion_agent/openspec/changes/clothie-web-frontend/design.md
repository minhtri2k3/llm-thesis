# Design: Clothie Web Frontend

## Directory Structure

```
llm-thesis/
├── fashion_agent/              (existing BE)
│   ├── api/main.py             ← add 2 endpoints
│   ├── agent/memory.py         ← add user_ratings DDL
│   ├── docker-compose.yml      ← add clothie-web + cloudflared-fe, remove old cloudflared
│   └── openspec/changes/clothie-web-frontend/
│
└── clothie_web/                (new Flutter Web project)
    ├── lib/
    │   ├── main.dart
    │   ├── config.dart         (API base url = '' for relative)
    │   ├── screens/
    │   │   ├── splash_screen.dart
    │   │   ├── register_screen.dart
    │   │   ├── chat_screen.dart
    │   │   └── rating_screen.dart
    │   ├── models/
    │   │   ├── chat_message.dart
    │   │   └── product.dart
    │   ├── services/
    │   │   └── api_service.dart
    │   └── widgets/
    │       ├── flying_icon_bg.dart   (animated background)
    │       ├── chat_bubble.dart
    │       ├── thinking_indicator.dart
    │       ├── product_card.dart
    │       └── star_rating.dart
    ├── pubspec.yaml
    ├── Dockerfile              (multi-stage: flutter-build + nginx-serve)
    ├── nginx.conf
    └── web/
        └── index.html
```

---

## Backend Changes

### New DB Schema (in `agent/memory.py` → `init_memory_tables()`)

```sql
-- Add user_name to existing sessions table
ALTER TABLE user_sessions
    ADD COLUMN IF NOT EXISTS user_name TEXT NOT NULL DEFAULT '';

-- New ratings table for thesis evaluation
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

### New Pydantic Models (in `api/main.py`)

```python
class CreateSessionRequest(BaseModel):
    user_name: str = ""

class CreateSessionResponse(BaseModel):
    session_id: str

class RatingRequest(BaseModel):
    session_id: str
    rating: int        # 1-10
    feedback: str = ""

class RatingResponse(BaseModel):
    ok: bool
```

### New Endpoints (in `api/main.py`)

```
POST /api/sessions
  body: { user_name: string }
  action: creates session via memory.create_session(), stores user_name
  returns: { session_id: string }

POST /api/rating
  body: { session_id: string, rating: int, feedback: string }
  action: inserts into user_ratings table
  returns: { ok: true }
```

---

## Flutter App Design

### Navigation Flow

```
SplashScreen  (2s timer)
     │  Navigator.pushReplacement
     ▼
RegisterScreen
     │  POST /api/sessions → { session_id }
     │  Navigator.pushReplacement
     ▼
ChatScreen                    (holds session_id)
     │  POST /api/chat/stream (SSE)
     │  "End session" button
     │  Navigator.push
     ▼
RatingScreen                  (holds session_id + user_name)
     │  POST /api/rating
     │  Navigator.pushAndRemoveUntil → SplashScreen (reset)
```

### State: ChatScreen

```dart
class ChatState {
  List<ChatMessage> messages;          // all messages (user + AI)
  String streamingBuffer;              // current AI response being built
  ThinkingStatus thinkingStatus;       // idle | thinking | streaming | done
  List<ThinkingStep> thinkingSteps;    // progressive thinking steps
  List<Product> pendingProducts;       // from "products" SSE event
  bool isLoading;
  String? sessionId;
}

enum ThinkingStatus { idle, thinking, streaming, done }
```

### SSE Parsing (api_service.dart)

```dart
// POST SSE via http.StreamedRequest — works in Flutter Web
Stream<SseEvent> chatStream(String message, String sessionId) async* {
  final request = http.Request('POST', Uri.parse('$baseUrl/api/chat/stream'));
  request.headers['Content-Type'] = 'application/json';
  request.body = jsonEncode({'message': message, 'session_id': sessionId});
  
  final response = await _client.send(request);
  
  String eventType = '';
  String dataStr = '';
  
  await for (final line in response.stream
      .transform(utf8.decoder)
      .transform(const LineSplitter())) {
    if (line.startsWith('event: ')) {
      eventType = line.substring(7);
    } else if (line.startsWith('data: ')) {
      dataStr = line.substring(6);
    } else if (line.isEmpty && eventType.isNotEmpty) {
      yield SseEvent(type: eventType, data: jsonDecode(dataStr));
      eventType = '';
      dataStr = '';
    }
  }
}
```

### SSE Event → UI Mapping

| SSE Event | UI Action |
|---|---|
| `thinking_start` | Set status=thinking, show 🤔 indicator |
| `thinking_step` | Append step text to thinking steps list |
| `thinking_end` | Set status=streaming, show collapsed thinking block |
| `token` | Append text to streamingBuffer, update AI bubble |
| `clarification` | Append to streamingBuffer |
| `products` | Store products list, show cards below the message |
| `done` | Set status=done, finalize message, append styling tip |

---

## Docker Architecture

### clothie_web/Dockerfile (multi-stage)

```
Stage 1 — builder:
  FROM ghcr.io/cirruslabs/flutter:stable
  WORKDIR /app
  COPY pubspec.* ./
  RUN flutter pub get
  COPY . .
  RUN flutter build web --release

Stage 2 — serve:
  FROM nginx:alpine
  COPY --from=builder /app/build/web /usr/share/nginx/html
  COPY nginx.conf /etc/nginx/conf.d/default.conf
  EXPOSE 80
```

### clothie_web/nginx.conf

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # Flutter SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API reverse proxy (routes to fashion-api on Docker internal network)
    location /api/ {
        proxy_pass http://fashion-api:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # SSE-critical: disable buffering
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_set_header Connection '';
        chunked_transfer_encoding on;
    }
}
```

### docker-compose.yml additions (in fashion_agent/)

```yaml
  clothie-web:
    build:
      context: ../clothie_web
      dockerfile: Dockerfile
    container_name: fashion-clothie-web
    restart: unless-stopped
    networks:
      - internal          # needs internal to resolve fashion-api hostname
    ports:
      - "3000:80"         # local dev access

  cloudflared-fe:
    image: cloudflare/cloudflared:latest
    container_name: fashion-cloudflared-fe
    restart: unless-stopped
    command: tunnel run
    environment:
      TUNNEL_TOKEN: ${CF_FE_TUNNEL_TOKEN:?CF_FE_TUNNEL_TOKEN is required}
    networks:
      - internal          # resolves clothie-web hostname for Cloudflare routing
    depends_on:
      - clothie-web
```

Remove the old `cloudflared` service entirely.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Relative `/api/` URLs | No hostname baked into Flutter JS → works on any Cloudflare URL |
| Nginx reverse proxy | Zero CORS, SSE works, clean same-origin architecture |
| `package:http` for SSE | Flutter Web compatible, no native EventSource (GET-only) needed |
| `Provider` for state | Lightweight, sufficient for single-chat-session state |
| `cirruslabs/flutter` Docker | Official-ish Flutter Docker image, multi-arch support |
| Cloth icon = `👗` emoji | Simple, no asset needed, animates the same |
| 1-10 stars in a Row | More granular ratings for thesis evaluation |
| Cloudflare "llm-thesis" tunnel | Pre-existing, configured in dashboard to `http://clothie-web:80` |

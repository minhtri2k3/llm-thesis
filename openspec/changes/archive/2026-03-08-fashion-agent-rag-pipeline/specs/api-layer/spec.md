## ADDED Requirements

### Requirement: Chat endpoint
The system SHALL expose a `POST /api/chat` endpoint accepting JSON body `{query: str, session_id?: str}` and returning the agent's structured response.

#### Scenario: New chat
- **WHEN** POST /api/chat with `{"query": "tìm áo sơ mi trắng"}`
- **THEN** system returns 200 with `{answer, products: [...], session_id, reasoning}`

#### Scenario: Continued conversation
- **WHEN** POST /api/chat with `{"query": "tìm thêm cái tương tự", "session_id": "abc123"}`
- **THEN** system loads conversation history for session abc123 and returns contextual response

### Requirement: Products endpoint
The system SHALL expose a `GET /api/products` endpoint for browsing products with optional filters (category, color, limit, offset).

#### Scenario: Browse products
- **WHEN** GET /api/products?category=Shirt&limit=20
- **THEN** system returns 200 with list of 20 shirt products from PostgreSQL

### Requirement: Image serving
The system SHALL expose a `GET /api/images/{image_id}` endpoint serving product images from the mounted images directory.

#### Scenario: Image retrieval
- **WHEN** GET /api/images/abc123
- **THEN** system returns the image file with appropriate Content-Type header (image/jpeg or image/png)

#### Scenario: Missing image
- **WHEN** GET /api/images/nonexistent
- **THEN** system returns 404 Not Found

### Requirement: Health check endpoint
The system SHALL expose a `GET /api/health` endpoint returning service status including PostgreSQL and Qdrant connectivity.

#### Scenario: All healthy
- **WHEN** GET /api/health and all services are running
- **THEN** system returns 200 with `{status: "healthy", postgres: "ok", qdrant: "ok", models_loaded: true}`

#### Scenario: Degraded state
- **WHEN** GET /api/health and Qdrant is unreachable
- **THEN** system returns 503 with `{status: "degraded", postgres: "ok", qdrant: "error"}`

### Requirement: Gradio UI
The system SHALL mount a Gradio chat interface at the root path `/`, providing a visual demo for thesis presentation.

#### Scenario: Web UI access
- **WHEN** user navigates to `https://fashion-agent.domain.com/`
- **THEN** a Gradio chatbot interface is displayed with a text input field and product result cards

### Requirement: CORS configuration
The system SHALL configure CORS to allow requests from the Cloudflare Tunnel domain.

#### Scenario: Cross-origin request
- **WHEN** browser makes a request from the configured domain
- **THEN** CORS headers allow the request

## 1. Docker Infrastructure Setup

- [x] 1.1 Create `docker-compose.yml` with 4 services: postgres (16-alpine), qdrant (latest), fashion-api (build context), cloudflared (latest)
- [x] 1.2 Create `.env.example` template with PG_PASSWORD, GEMINI_API_KEY, CF_TUNNEL_TOKEN placeholders
- [x] 1.3 Configure internal bridge network — postgres and qdrant NOT exposed to host
- [x] 1.4 Add named volumes (pgdata, qdrant_data) for data persistence
- [x] 1.5 Add PostgreSQL healthcheck (`pg_isready`) and fashion-api depends_on with condition
- [x] 1.6 Verify stack: `docker compose up -d postgres qdrant` → both healthy

## 2. Data Ingestion Migration (processing_data.py)

- [x] 2.1 Remove GCP imports and dependencies: gcloud, ADC token, cloud-sql-proxy socket checks
- [x] 2.2 Remove `check_gcloud_exists()`, `check_adc_token()`, `check_proxy_socket()` from doctor command
- [x] 2.3 Remove `GCP_PROJECT_ID` and `INSTANCE_CONNECTION_NAME` env vars from config
- [x] 2.4 Simplify `run_doctor()` to only check PostgreSQL connectivity via psycopg2
- [x] 2.5 Update `GoogleDatabaseConfig` → `DatabaseConfig` with Docker-compatible defaults (host=localhost, port=5432)
- [x] 2.6 Verify: `python processing_data.py doctor` connects to Docker PostgreSQL
- [x] 2.7 Verify: `python processing_data.py init-db` creates tables in Docker PostgreSQL
- [x] 2.8 Verify: `python processing_data.py ingest-kaggle` upserts data successfully

## 3. Embedding & Indexing Pipeline (build_index.py)

- [x] 3.1 Create `indexing/build_index.py` with CLI (argparse: init, build, status subcommands)
- [x] 3.2 Implement FashionSigLIP model loading from `Marqo/marqo-fashionSigLIP` with HF cache in `models/`
- [x] 3.3 Implement `init` command: create Qdrant collection `fashion_products` (vector_size=768, distance=Cosine)
- [x] 3.4 Implement image encoding function: single image → 768d vector (FP16)
- [x] 3.5 Implement batch encoding with configurable batch_size (default 32)
- [x] 3.6 Implement `build` command: read PG → encode images → compose payloads → upsert Qdrant
- [x] 3.7 Compose `bm25_content` as `"{label}. {color}."` for each item
- [x] 3.8 Implement incremental indexing: skip items already in Qdrant (check point_ids)
- [x] 3.9 Implement BM25 index construction (in-memory, using rank_bm25 library)
- [x] 3.10 Implement `status` command: show count of items in PG vs Qdrant
- [x] 3.11 Verify: `python build_index.py init && python build_index.py build` → Qdrant has vectors

## 4. Hybrid Search Pipeline

- [x] 4.1 Create `search/search_engine.py` with `search(query: str) -> List[NodeWithScore]` main function
- [x] 4.2 Implement query text encoding using FashionSigLIP (shared model instance from indexing)
- [x] 4.3 Implement BM25 retriever: tokenize query → search BM25 index → top-20 results
- [x] 4.4 Implement Vector retriever: encode query → Qdrant ANN search → top-20 results
- [x] 4.5 Create `search/fusion.py` with RRF Fusion (k=60, bm25_weight=1.0, vec_weight=2.5)
- [x] 4.6 Implement Soft Relevance Filter using RapidFuzz fuzzy matching (threshold=60)
- [x] 4.7 Create `search/reranker.py` — load `BAAI/bge-reranker-v2-m3` and rerank filtered nodes → top-6
- [x] 4.8 Implement reranker input limit: max 20 nodes sent to cross-encoder
- [x] 4.9 Verify end-to-end: `search("white formal shirt")` returns 6 relevant products

## 5. Fashion Agent Logic

- [x] 5.1 Create `agent/intent_classifier.py` using Gemini: classify query → search/recommend/chat/clarify
- [x] 5.2 Create `agent/clarification_gate.py`: detect vague queries → ask clarifying questions
- [x] 5.3 Create `agent/memory.py`: PostgreSQL tables (user_sessions, conversation_history) + CRUD functions
- [x] 5.4 Create `agent/fashion_agent.py` with main `chat(query, session_id) -> AgentResponse` function
- [x] 5.5 Implement ReAct loop: reason → search → observe → refine (max 2 iterations)
- [x] 5.6 Implement Gemini 2.5 Pro synthesis: top-6 products + query + history → structured response
- [x] 5.7 Define AgentResponse dataclass: answer, products, styling_suggestion, reasoning, session_id
- [x] 5.8 Verify: `agent.chat("tìm áo sơ mi trắng", None)` returns structured response

## 6. API Layer

- [x] 6.1 Create `api/main.py` with FastAPI app
- [x] 6.2 Implement `POST /api/chat` endpoint (JSON body: query, session_id optional)
- [x] 6.3 Implement `GET /api/products` endpoint (query params: category, color, limit, offset)
- [x] 6.4 Implement `GET /api/images/{image_id}` endpoint (serve from mounted images dir)
- [x] 6.5 Implement `GET /api/health` endpoint (check PG + Qdrant + models_loaded)
- [x] 6.6 Mount Gradio chat interface at root `/`
- [x] 6.7 Configure CORS for Cloudflare Tunnel domain
- [x] 6.8 Verify: `uvicorn api.main:app --port 8000` → all endpoints respond correctly

## 7. Containerize & Deploy

- [x] 7.1 Create multi-stage `Dockerfile`: builder (install deps) → runtime (slim image)
- [x] 7.2 Configure model volume mount in docker-compose.yml (./models:/app/models:ro)
- [x] 7.3 Configure images volume mount (./images:/app/images:ro)
- [x] 7.4 Add cloudflared service with CF_TUNNEL_TOKEN environment variable
- [x] 7.5 Full stack test: `docker compose up -d` → all 4 containers healthy
- [ ] 7.6 Verify Cloudflare Tunnel: `curl https://fashion-agent.domain.com/api/health` → 200 OK
- [ ] 7.7 End-to-end test: query via public URL → search → rerank → Gemini synthesis → response

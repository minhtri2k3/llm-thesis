# 🛍️ Fashion Agent Multimodal

> Hệ thống tìm kiếm thời trang thông minh dựa trên **RAG** (Retrieval-Augmented Generation) và kiến trúc **Agent ReAct** — PATH 1: Text-to-Image Search.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-purple?logo=google)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## 📋 Mục lục

- [Tổng quan](#-tổng-quan)
- [Tính năng chính](#-tính-năng-chính)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Tech Stack](#-tech-stack)
- [Cấu trúc dự án](#-cấu-trúc-dự-án)
- [Chi tiết từng module](#-chi-tiết-từng-module)
- [API Endpoints](#-api-endpoints)
- [Luồng xử lý Runtime](#-luồng-xử-lý-runtime-query--response)
- [Hướng dẫn cài đặt & chạy](#-hướng-dẫn-cài-đặt--chạy)
- [Đóng góp code (cho thành viên nhóm)](#-đóng-góp-code-cho-thành-viên-nhóm)
- [Lộ trình phát triển](#-lộ-trình-phát-triển)
- [License](#-license)

---

## 🎯 Tổng quan

Fashion Agent là hệ thống **AI Agent** giúp người dùng tìm kiếm sản phẩm thời trang bằng ngôn ngữ tự nhiên (tiếng Việt / tiếng Anh). Thay vì pipeline cố định, Agent chủ động:

1. **Hiểu ý định** — phân loại query thành 5 intent types
2. **Thu thập đủ thông tin** — slot-based clarification: hỏi CỤ THỂ cái thiếu (loại, màu, chất liệu, dáng, phong cách)
3. **Nhớ sở thích** — lưu trữ preferences qua PostgreSQL sessions
4. **Tự lập kế hoạch** — ReAct loop (Reason → Act → Observe), tối đa 8 vòng
5. **Trả lời tự nhiên** — Gemini tổng hợp câu trả lời + gợi ý phối đồ

### So sánh RAG v1.0 → Agent v2.0

| Tiêu chí | RAG v1.0 | Agent v2.0 |
|----------|----------|------------|
| Xử lý truy vấn | Pipeline cứng 9 bước | ReAct loop tự quyết định |
| Truy vấn mơ hồ | Tìm với thông tin thiếu | Slot-based clarification |
| Ngữ cảnh | Không nhớ giữa các lượt | MemoryAgent lưu sở thích phiên |
| Lưu trữ | CSV cục bộ | PostgreSQL (triển khai server) |
| Từ chối lịch sự | Không có | Phát hiện out-of-scope |
| Kết quả | Danh sách sản phẩm | Sản phẩm + lý luận + gợi ý phối đồ |
| Embedding | FashionCLIP (512-d) | Marqo-FashionSigLIP (768-d) |
| Query Expansion | Không có | Gemini sinh synonym queries |
| Reranker | Không có | BGE Reranker v2-m3 (cross-encoder) |

---

## ✨ Tính năng chính

### 🎯 Slot-Based Clarification (Mới)

Agent thu thập thông tin theo **6 slots** trước khi tìm kiếm, đảm bảo kết quả chính xác:

```
User query → Extract 6 slots → Đủ thông tin?
  ├── ✅ YES → Search ngay (0 câu hỏi thừa)
  └── ❌ NO  → Hỏi CỤ THỂ cái thiếu → merge → check lại (max 3 lần)
```

**6 slots thông tin:**

| Slot | Mô tả | Ví dụ |
|------|--------|-------|
| `category` | Loại trang phục | Shirt, Dress, Pants |
| `color` | Màu sắc | white, navy blue, red |
| `fabric` | Chất liệu | cotton, silk, denim |
| `fit` | Dáng/kiểu | slim fit, oversized, A-line |
| `construction` | Chi tiết | cổ bẻ, zip closure |
| `aesthetic` | Phong cách | casual, formal, minimalist |

**Ngưỡng tìm kiếm:** `category + color + 3/4 caption slots` → search ngay.

**Ví dụ:**
```
User: "tìm áo sơ mi trắng cotton, dáng slim fit, phong cách minimalist"
→ 5/6 slots ✅ → Search ngay, không hỏi thêm 🚀

User: "tìm áo trắng"
→ 2/6 slots ❌ → "Bạn thích chất liệu gì? Dáng thế nào? Phong cách nào?"
```

### 🔍 Hybrid Search Pipeline (7 stages)

```
Query Expansion (Gemini) → BM25 (top-20) + Image Vec (top-20) + Text Vec (top-20)
    → Dedup Merge → RRF Fusion → Soft Filter → BGE Rerank → Top-6
```

- **BM25**: Tìm chính xác theo category + màu sắc (`rank_bm25`)
- **Image Vector**: Visual matching bằng [Marqo-FashionSigLIP](https://huggingface.co/Marqo/marqo-fashionSigLIP) (768-d) trên Qdrant
- **Text Vector**: Semantic matching (label + color + caption) trên Qdrant
- **RRF Fusion**: Kết hợp 3 retriever sources (k=60, weights tunable)
- **Soft Filter**: RapidFuzz fuzzy matching trên color + label
- **BGE Reranker**: Cross-encoder reranking cho precision cao

### 🤖 Agent ReAct Loop

```
① Intent Classify + Slot Extract (Gemini, 1 LLM call)
    → ② Slot Completeness Check (nếu text_search)
    → ③ Targeted Clarification (nếu thiếu slots)
    → ④ Memory Load (preferences từ PostgreSQL)
    → ⑤ ReAct Loop: Plan → Execute → Observe (max 8 vòng)
    → ⑥ Synthesize (Gemini → answer + styling tips)
```

### 🧠 5 Intent Types

| Intent | Mô tả | Hành động |
|--------|--------|-----------|
| `text_search` | Tìm sản phẩm cụ thể | Slot check → tìm kiếm |
| `outfit_request` | Gợi ý trang phục | Tìm + phối đồ |
| `follow_up` | Tham chiếu lượt trước | Merge slots + tìm kiếm |
| `out_of_scope` | Không liên quan thời trang | Từ chối lịch sự |
| `unclear` | Mơ hồ | Hỏi làm rõ |

### 💾 Session Memory (PostgreSQL)

- Lưu lịch sử query + liked items qua JSONB
- Tự tổng hợp top-3 preferred colors/categories
- Hỗ trợ multi-turn conversation
- Accumulated slots per session (slot merging qua các turns)

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                     Gradio UI (:8000)                   │
│                   FastAPI Backend                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐   ┌────────────────┐   ┌──────────────┐  │
│  │  Intent   │──▶│  Slot-Based    │──▶│   Memory     │  │
│  │Classifier │   │ Clarification  │   │   Agent      │  │
│  │+ Slot     │   │  (targeted Q)  │   │ (PostgreSQL) │  │
│  │ Extract   │   └────────────────┘   └──────────────┘  │
│  │ (Gemini)  │                                          │
│  └──────────┘                                           │
│        │                                                │
│        ▼                                                │
│  ┌─────────────────────────────────────────────┐        │
│  │           ReAct Loop (max 8 iter)           │        │
│  │  ┌──────────────────────────────────────┐   │        │
│  │  │ Plan (Gemini) → Execute → Observe    │   │        │
│  │  └──────────────────────────────────────┘   │        │
│  │  Tools:                                     │        │
│  │    • search(query) → Hybrid Search Pipeline │        │
│  │    • memory_enrich(query, prefs)            │        │
│  │    • outfit_hints(occasion, style)          │        │
│  └─────────────────────────────────────────────┘        │
│        │                                                │
│        ▼                                                │
│  ┌──────────────────────────────────────────┐           │
│  │        Hybrid Search Pipeline            │           │
│  │  Query Expansion → BM25 + ImgVec + TxtVec│          │
│  │    → RRF Fusion → Soft Filter → Rerank  │           │
│  └──────────────────────────────────────────┘           │
│        │                      │                         │
├────────┼──────────────────────┼─────────────────────────┤
│        ▼                      ▼                         │
│  ┌──────────┐          ┌──────────────┐                 │
│  │  Qdrant  │          │  PostgreSQL  │                 │
│  │ (Vectors)│          │   (Items +   │                 │
│  │  :6333   │          │   Sessions)  │                 │
│  └──────────┘          │    :5432     │                 │
│                        └──────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
Phase 0 (Offline): Kaggle CSV → PostgreSQL → Gemini Enrichment (caption + color)
Phase 1 (Offline): PostgreSQL → FashionSigLIP encode → Qdrant upsert + BM25 build
Phase 2 (Runtime): User Query → Slot Check → Agent ReAct → Hybrid Search → LLM Synthesis → Response
```

---

## 🛠️ Tech Stack

| Layer | Technology | Vai trò |
|-------|-----------|---------| 
| **LLM** | Gemini 2.5 Flash | Intent + Slot Extract, Planning, Synthesis, Caption |
| **Embedding** | Marqo-FashionSigLIP (768-d) | Image + Text semantic encoding |
| **Vector DB** | Qdrant (2 named vectors) | ANN search (image_vector, text_vector) |
| **Keyword Search** | rank_bm25 (BM25Okapi) | Exact category + color matching |
| **Reranker** | BAAI/bge-reranker-v2-m3 | Cross-encoder precision boost |
| **Fuzzy Match** | RapidFuzz | Soft relevance filtering |
| **Database** | PostgreSQL 16 | Items, sessions, messages |
| **API** | FastAPI + Gradio | REST API + Chat UI |
| **Deployment** | Docker Compose (4 services) | PostgreSQL, Qdrant, App, Cloudflare |
| **Tunnel** | Cloudflare Tunnel | Public HTTPS access |

---

## 📁 Cấu trúc dự án

```
fashion_agent/
├── api/
│   └── main.py                # FastAPI + Gradio UI
├── agent/
│   ├── fashion_agent.py       # ReAct orchestrator + slot integration
│   ├── intent_classifier.py   # LLM intent + 6 slot extraction
│   ├── slot_completeness.py   # Slot check, merge, targeted questions
│   ├── clarification_gate.py  # Generic clarification (non-text_search)
│   └── memory.py              # PostgreSQL session memory
├── search/
│   ├── search_engine.py       # Hybrid search pipeline (3 retrievers)
│   ├── query_expansion.py     # Gemini query expansion
│   ├── fusion.py              # RRF Fusion (3-source)
│   └── reranker.py            # BGE cross-encoder reranker
├── indexing/
│   └── build_index.py         # FashionSigLIP + Qdrant indexing
├── pre_processing/
│   └── processing_data.py     # Kaggle → PostgreSQL + Gemini enrichment
├── documents/
│   ├── Fashion_Agent_Report.pdf
│   └── Fashion_Agent_Report_v2.tex
├── docker-compose.yml         # 4-service stack
├── Dockerfile                 # Multi-stage build
├── requirements-docker.txt    # Python dependencies
├── .env.example               # Environment template
└── README.md                  # ← Bạn đang đây
```

---

## 🔬 Chi tiết từng module

### `agent/` — Bộ não của hệ thống

#### `fashion_agent.py` ⭐ (531 LOC) — ReAct Orchestrator

File **quan trọng nhất** — điều phối toàn bộ luồng xử lý từ lúc nhận query đến khi trả response.

| Thành phần | Mô tả |
|------------|--------|
| `chat(query, session_id)` | **Hàm chính** — entry point duy nhất, trả về `AgentResponse` |
| `AgentResponse` | Dataclass chứa: `answer`, `products[]`, `styling_suggestion`, `reasoning`, `session_id`, `intent` |
| `ProductResult` | Dataclass cho mỗi sản phẩm: `image_id`, `label`, `color`, `caption`, `score` |
| `_plan()` | Gemini quyết định gọi tool nào tiếp theo (ReAct reasoning) |
| `_execute_tool()` | Thực thi tools: `search`, `memory_enrich`, `outfit_hints` |
| `_synthesize_response()` | Gemini tổng hợp kết quả thành câu trả lời tự nhiên + styling tips |
| `_count_clarification_turns()` | Đếm số lần đã hỏi clarification (max 3) |

**Constants:**
- `MAX_REACT_ITERATIONS = 8` — giới hạn vòng lặp ReAct
- `MAX_CLARIFICATION_TURNS = 3` — max số lần hỏi clarification
- `LOW_CONFIDENCE_THRESHOLD = 0.5` — ngưỡng confidence thấp

**ReAct Tools:**

| Tool | Args | Chức năng |
|------|------|-----------|
| `search` | `query: str, top_k: int` | Gọi hybrid search pipeline |
| `memory_enrich` | `query: str, prefs: dict` | Enrich query bằng user preferences |
| `outfit_hints` | `occasion: str, style: str` | Gợi ý phối đồ theo dịp/phong cách |

---

#### `intent_classifier.py` (210 LOC) — Phân loại ý định + Trích xuất slots

Dùng **1 Gemini call duy nhất** để vừa phân loại intent vừa extract 6 slots.

| Thành phần | Mô tả |
|------------|--------|
| `classify_intent(query, history)` | **Hàm chính** → trả `ClassifiedIntent` |
| `ClassifiedIntent` | Dataclass: `intent`, `confidence`, `filters`, `refined_query`, `extracted_slots` |
| `ExtractedSlots` | 6 slots: `category`, `color`, `fabric`, `fit`, `construction`, `aesthetic` |
| `ExtractedSlots.filled_count()` | Đếm slots đã điền (không null/rỗng) |
| `ExtractedSlots.caption_slots_filled()` | Đếm 4 caption slots đã điền |
| `ExtractedSlots.missing_slots()` | Trả tên các slots còn thiếu |

---

#### `slot_completeness.py` (243 LOC) — Logic kiểm tra + merge slots

| Hàm | Input → Output | Mô tả |
|-----|----------------|--------|
| `check_slot_completeness(slots)` | `ExtractedSlots` → `(bool, list[str])` | Kiểm tra đã đủ để search chưa. Threshold: `category ✅ + color ✅ + ≥3/4 caption slots` |
| `generate_targeted_question(slots, missing, history)` | slots + missing → `str` | Gemini sinh câu hỏi tự nhiên, hỏi CỤ THỂ cái thiếu |
| `merge_slots(accumulated, new)` | 2 slots → merged | Merge qua nhiều turns (non-null mới ghi đè cũ) |
| `should_reset_slots(accumulated, new)` | 2 slots → `bool` | Reset khi user đổi `category` (chủ đề mới) |
| `compose_refined_query_from_slots(slots)` | slots → `str` | Ghép slots thành search query: `"white cotton slim fit Shirt"` |

---

#### `clarification_gate.py` (110 LOC) — Hỏi làm rõ khi query mơ hồ

| Hàm | Mô tả |
|-----|--------|
| `check_clarification(query, history)` | Gemini sinh câu hỏi clarification cho intent `unclear` hoặc confidence < 0.5 |

Trả về `ClarificationResult(needs_clarification=True, question="...")`. Có fallback nếu không có Gemini API key.

---

#### `memory.py` (288 LOC) — Session Memory trên PostgreSQL

| Hàm | Mô tả |
|-----|--------|
| `init_memory_tables()` | Tạo bảng `sessions` + `messages` nếu chưa có |
| `create_session()` | Tạo session mới, trả UUID |
| `session_exists(session_id)` | Kiểm tra session tồn tại |
| `add_message(session_id, role, content)` | Lưu tin nhắn vào history |
| `get_history(session_id, limit=20)` | Lấy lịch sử chat gần nhất |
| `log_query(session_id, query, intent, filters)` | Log query vào `query_history` JSONB |
| `get_preferences(session_id)` | Phân tích → top-3 preferred colors/categories/styles |

**Schema:**
- `sessions`: `session_id UUID PK`, `query_history JSONB`, `liked_items JSONB`, `created_at`, `updated_at`
- `messages`: `id SERIAL PK`, `session_id FK`, `role`, `content`, `created_at`

---

### `search/` — Hybrid Search Pipeline

#### `search_engine.py` ⭐ (390 LOC) — 7-stage search

| Hàm/Component | Mô tả |
|----------------|--------|
| `search(query, top_k=6)` | **Hàm chính** — chạy toàn bộ 7 stages, trả `list[NodeWithScore]` |
| `bm25_retrieve(query, top_k=20)` | BM25 keyword search (label + color) |
| `vector_retrieve(query, top_k=20)` | Qdrant ANN search trên `image_vector` (SigLIP 768-d) |
| `text_vector_retrieve(query, top_k=20)` | Qdrant ANN search trên `text_vector` (SigLIP text encoder) |
| `soft_relevance_filter(query, nodes)` | RapidFuzz fuzzy match trên color + label |
| `_dedup_merge(nodes)` | Loại trùng theo `image_id`, giữ score cao nhất |
| `_compute_filter_relevance(node, filters)` | Boost/penalize dựa trên intent filters |

**7 Stages:**
```
0. Query Expansion (Gemini sinh 3 synonym queries, chỉ query ngắn < 6 từ)
1. BM25 Retrieve (top-20 per expanded query)
2. Image Vector ANN (top-20 per query, SigLIP encode text → search image space)
3. Text Vector ANN (top-20 per query, SigLIP encode text → search text space)
4. Dedup Merge (giữ score cao nhất per image_id)
5. RRF Fusion (k=60, weights: BM25=2.5, ImgVec=1.0, TxtVec=1.5)
6. Soft Filter (RapidFuzz fuzzy matching, threshold=40)
7. BGE Rerank (cross-encoder scoring → top-6)
```

**Singleton models** (load 1 lần, dùng mãi):
- `_embedder` → `FashionEmbedder` (SigLIP model)
- `_bm25_index` → BM25Okapi (rebuild từ Qdrant payloads khi startup)

---

#### `fusion.py` (85 LOC) — RRF Fusion

| Thành phần | Mô tả |
|------------|--------|
| `NodeWithScore` | Dataclass: `image_id`, `label`, `color`, `caption`, `image_path`, `bm25_content`, `score` |
| `reciprocal_rank_fusion(bm25, vec, text_vec)` | Merge 3 nguồn bằng công thức RRF |

**Công thức:**
```
rrf_score = 2.5 × 1/(60 + rank_bm25 + 1)
          + 1.0 × 1/(60 + rank_img  + 1)
          + 1.5 × 1/(60 + rank_text + 1)
```

---

#### `reranker.py` (134 LOC) — BGE Cross-Encoder

| Thành phần | Mô tả |
|------------|--------|
| `BGEReranker` class | Model: `BAAI/bge-reranker-v2-m3`, device: MPS (M1 Mac) hoặc CPU |
| `reranker.rerank(query, nodes, top_k=6)` | Cross-encoder scoring + score blending |
| `get_reranker()` | Singleton factory |

**Score blending:** `final = 0.7 × normalized_reranker + 0.3 × original_RRF_score`

---

#### `query_expansion.py` (106 LOC) — Gemini Synonym Expansion

| Hàm | Mô tả |
|-----|--------|
| `expand_query(query, max_expansions=3)` | Sinh synonym queries bằng Gemini |

**Ví dụ:** `"red dress"` → `["red dress", "crimson gown", "scarlet formal dress"]`

**Gate:** Chỉ expand khi query < 6 từ (short query gate).

---

### `indexing/` — Offline Index Building

#### `build_index.py` (519 LOC) — SigLIP Encode → Qdrant

| Thành phần | Mô tả |
|------------|--------|
| `FashionEmbedder` class | Wrapper cho `Marqo/marqo-fashionSigLIP` — encode image/text ra 768-d vector |
| `FashionEmbedder.encode_image(path)` | Encode 1 ảnh → vector 768-d |
| `FashionEmbedder.encode_images_batch(paths, batch=16)` | Encode batch → tiết kiệm thời gian |
| `FashionEmbedder.encode_text(text)` | Encode text → vector 768-d |
| `init_collection(client)` | Tạo Qdrant collection `fashion_products` với 2 named vectors |
| `run_build(cfg)` | Pipeline chính: PG → encode → Qdrant upsert |
| `run_status(cfg)` | In thống kê hiện tại (PG items, Qdrant points) |
| `compose_bm25_content(item)` | Ghép `label + color` cho BM25 |
| `compose_text_embed_content(item)` | Ghép `label + color + caption` cho text embedding |

**Qdrant collection `fashion_products`:**
- Named vector `image_vector`: Cosine, 768-d
- Named vector `text_vector`: Cosine, 768-d
- Payloads: `image_id`, `label`, `color`, `caption`, `image_path`, `bm25_content`

---

### `pre_processing/` — Data Ingestion

#### `processing_data.py` (698 LOC) — Kaggle → PostgreSQL + Gemini Enrichment

| Thành phần | Mô tả |
|------------|--------|
| `FashionDatabase` class | CRUD PostgreSQL: `init_tables()`, `upsert_items()`, `fetch_missing_captions()`, `fetch_missing_colors()` |
| `GeminiFashionProcessor` class | Gemini vision: `generate_search_caption(image)`, `detect_item_color(image, label)` |
| `load_kaggle_rows_for_upsert()` | Download + filter dataset Kaggle (loại bỏ "Not sure", "Skip", "Other") |
| `process_missing_captions(db, processor)` | Batch sinh caption cho items chưa có |
| `process_missing_colors(db, processor)` | Batch detect color cho items chưa có |
| `run_doctor(config)` | Kiểm tra kết nối PostgreSQL (Docker + local) |

**PostgreSQL tables:**
- `fashion_items`: `image_id PK`, `label`, `image_path`, `source`
- `fashion_item_enrichment`: `image_id FK`, `caption`, `color`, `model_name`
- `processing_log`: `image_id`, `step`, `status`, `message`

---

### `api/` — FastAPI + Gradio UI

#### `main.py` (376 LOC) — Entry Point

| Thành phần | Mô tả |
|------------|--------|
| `app` | FastAPI instance, mount Gradio tại root `/` |
| `lifespan()` | Startup → `init_memory_tables()` |
| `create_gradio_app()` | Chat UI: textbox + chatbot + product images |
| `_convert_image_path()` | Map host path → container path cho Docker |

---

## 🌐 API Endpoints

| Method | Path | Request | Response | Mô tả |
|--------|------|---------|----------|--------|
| `GET` | `/` | — | HTML | Gradio Chat UI |
| `POST` | `/api/chat` | `{"message": "...", "session_id": "..." \| null}` | `ChatResponse` | Agent chat chính |
| `GET` | `/api/products/{image_id}` | — | Product JSON | Lấy chi tiết sản phẩm |
| `GET` | `/api/images/{filename}` | — | File | Serve ảnh sản phẩm |
| `GET` | `/health` | — | `HealthResponse` | Health check (PG + Qdrant) |

### `POST /api/chat` — Chi tiết

**Request:**
```json
{
  "message": "tìm áo sơ mi trắng cotton, dáng slim fit",
  "session_id": null
}
```

**Response:**
```json
{
  "answer": "Đây là 6 áo sơ mi trắng cotton slim fit phù hợp với bạn...",
  "products": [
    {
      "image_id": "ea7b6656",
      "image_path": "/path/to/ea7b6656.jpg",
      "label": "Shirt",
      "color": "white",
      "caption": "A slim fit white cotton button-down shirt...",
      "score": 0.85
    }
  ],
  "styling_suggestion": "Phối với quần chinos navy và giày loafer nâu...",
  "reasoning": "Found 6 matching white cotton shirts with slim fit...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "intent": "text_search"
}
```

### `GET /health` — Health Check

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "postgresql": "healthy",
    "qdrant": "healthy"
  }
}
```

---

## 🔄 Luồng xử lý Runtime (Query → Response)

Dưới đây là luồng xử lý **chi tiết** khi user gửi 1 tin nhắn. Teammate cần hiểu luồng này để biết sửa file nào khi cần.

### Bước 1 — Nhận request

```
User: "tìm áo sơ mi trắng cotton"
  → api/main.py: chat_endpoint()
  → agent/fashion_agent.py: chat()
```

### Bước 2 — Session Management

```
Nếu session_id == null:
  → memory.create_session() → UUID mới
  → memory.add_message(session_id, "user", query)
Nếu session_id có sẵn:
  → memory.get_history(session_id) → lịch sử chat
  → memory.add_message(session_id, "user", query)
```

### Bước 3 — Intent Classify + Slot Extract (1 Gemini call)

```
intent_classifier.classify_intent(query, history)
  → Gemini 2.5 Flash:
    intent: "text_search", confidence: 0.95
    extracted_slots: {
      category: "Shirt", color: "white", fabric: "cotton",
      fit: null, construction: null, aesthetic: null
    }
    filters: {"category": "Shirt", "color": "white"}
```

### Bước 4 — Slot Completeness Check (chỉ cho `text_search`)

```
slot_completeness.check_slot_completeness(slots)
  → category ✅, color ✅
  → caption_slots_filled = 1/4 (chỉ có fabric)
  → is_complete = False
  → missing = ["fit", "construction", "aesthetic"]
```

### Bước 5a — Nếu THIẾU slots → Targeted Clarification

```
slot_completeness.generate_targeted_question(slots, missing, history)
  → Gemini: "Bạn muốn dáng gì (slim fit, regular, oversized)?
    Chi tiết nào (cổ bẻ, cổ tròn)? Phong cách nào (casual, formal)?"
  → Trả AgentResponse(answer=question, intent="text_search")
  → DỪNG — chờ user trả lời
```

### Bước 5b — User trả lời → Slot Merge

```
Turn 2: User: "dáng slim fit, phong cách minimalist"
  → classify_intent() → new_slots: {fit: "slim fit", aesthetic: "minimalist"}
  → slot_completeness.merge_slots(accumulated, new_slots)
  → merged: {category: "Shirt", color: "white", fabric: "cotton",
              fit: "slim fit", aesthetic: "minimalist"}
  → check: caption_slots = 3/4 ✅ → SEARCH!
```

### Bước 6 — Memory Load

```
memory.get_preferences(session_id)
  → {preferred_colors: ["white"], preferred_categories: ["Shirt"]}
```

### Bước 7 — ReAct Loop (max 8 iterations)

```
Iteration 1:
  _plan(query, intent, preferences, observations=[], iter=1, max=8)
    → Gemini: [{"tool": "search", "args": {"query": "white cotton slim fit minimalist Shirt", "top_k": 6}}]
  _execute_tool("search", args)
    → search_engine.search() ← Bước 8
    → observation: "Found 6 products: Shirt(white), Shirt(white)..."
  Observations đủ? → Yes → Thoát loop
```

### Bước 8 — Hybrid Search Pipeline (bên trong `search()`)

```
0. compose_refined_query_from_slots() → "white cotton slim fit minimalist Shirt"
1. expand_query() → ["white cotton slim fit shirt", "minimalist white cotton shirt"]
2. Per expanded query:
   a. bm25_retrieve(query, top_k=20)        → 20 results (keyword match)
   b. vector_retrieve(query, top_k=20)      → 20 results (image space ANN)
   c. text_vector_retrieve(query, top_k=20) → 20 results (text space ANN)
3. _dedup_merge(all_results)                → loại trùng image_id
4. reciprocal_rank_fusion(bm25, img, txt)   → RRF scored list
5. soft_relevance_filter(query, fused)      → Fuzzy match filter
6. _compute_filter_relevance(node, filters) → Boost matching items
7. reranker.rerank(query, filtered, top_k=6) → Final top 6
```

### Bước 9 — Gemini Synthesis

```
_synthesize_response(query, products, history, intent, preferences)
  → Gemini 2.5 Flash:
    {
      "answer": "Đây là 6 áo sơ mi trắng cotton slim fit...",
      "styling_suggestion": "Phối với quần chinos navy và giày loafer..."
    }
```

### Bước 10 — Trả Response

```
memory.log_query(session_id, query, intent, filters)
memory.add_message(session_id, "assistant", answer)
→ AgentResponse(answer, products, styling_suggestion, reasoning, session_id, intent)
→ API trả ChatResponse JSON
→ Gradio hiển thị text + product images
```

### Tổng số Gemini calls per query (trường hợp search):

| Call | Mục đích | File |
|------|----------|------|
| 1 | Intent + Slot Extract | `intent_classifier.py` |
| 2 | Query Expansion (nếu query ngắn) | `query_expansion.py` |
| 3 | ReAct Planning | `fashion_agent.py` |
| 4 | Synthesis | `fashion_agent.py` |
| **Tổng** | **3-4 calls** | |

---

## 🗺️ Lộ trình phát triển

| Phase | Trạng thái | Nội dung |
|-------|-----------|----------|
| **Phase 1** — RAG v1.0 | ✅ Hoàn thành | Pipeline 9 bước, FashionCLIP, CSV |
| **Phase 2** — Agent v2.0 | ✅ Hoàn thành | ReAct loop, PostgreSQL, FashionSigLIP, Docker |
| **Phase 2.5** — Slot Clarification | ✅ Hoàn thành | 6-slot extraction, targeted questions, multi-turn merge |
| **Phase 3** — Scale | 📋 Kế hoạch | Dataset 15K→100K, Redis cache, fine-tune reranker |
| **Phase 4** — Advanced | 📋 Kế hoạch | Virtual Try-on (IDM-VTON), PATH 2: Image-to-Image |

---

## 📊 Chỉ số đánh giá (mục tiêu)

| Metric | RAG v1.0 | Agent v2.0 |
|--------|----------|------------|
| Recall@5 | ≥85% | ≥88% |
| MRR | ≥0.75 | ≥0.80 |
| Hit Rate@5 | ≥90% | ≥93% |
| Task Completion | N/A | ≥95% |
| Faithfulness | N/A | ≥0.87 |
| Latency P95 | <15s | <15s |

---

## ⚠️ Rủi ro đã xác định

| Rủi ro | Mức độ | Giải pháp |
|--------|--------|-----------|
| Latency cao (nhiều Gemini calls) | Cao | Parallel tool calls, cache expansion |
| Hallucination LLM | Cao | RAGAS faithfulness ≥0.87, fallback |
| BM25 rebuild khi khởi động | Thấp | Serialize BM25 index ra disk |
| Gemini API rate limit | Trung bình | Batch processing, exponential backoff |

---

## 🔧 Hướng dẫn cài đặt & chạy

### Yêu cầu hệ thống

| Yêu cầu | Phiên bản |
|----------|-----------|
| Docker + Docker Compose | v24+ |
| Python (nếu dev local) | 3.11+ |
| Git | 2.39+ |
| RAM | ≥8GB (khuyến nghị 16GB) |
| Disk | ~5GB (models + images) |
| Gemini API Key | [Lấy tại đây](https://aistudio.google.com/apikey) |

---

### 🚀 Quick Start — Docker (5 bước)

#### Bước 1: Clone repository

```bash
git clone https://github.com/minhtri2k3/llm-thesis.git
cd llm-thesis/fashion_agent
```

#### Bước 2: Cấu hình môi trường

```bash
# Copy file .env mẫu
cp .env.example .env
```

Mở file `.env` và điền giá trị:

```dotenv
# BẮT BUỘC — Mật khẩu PostgreSQL (tùy chọn, tự đặt)
PG_PASSWORD=your_secure_password_here

# BẮT BUỘC — API key Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# TÙY CHỌN — Cloudflare Tunnel token (bỏ trống nếu không dùng)
CF_TUNNEL_TOKEN=
```

#### Bước 3: Khởi động databases

```bash
# Khởi động PostgreSQL + Qdrant
docker compose up -d postgres qdrant

# Chờ cả hai healthy (~15 giây)
docker compose ps
```

Kết quả mong đợi:

```
NAME               STATUS
fashion-postgres   Up (healthy)
fashion-qdrant     Up (healthy)
```

#### Bước 4: Build và chạy API

```bash
# Build + chạy Fashion API (lần đầu ~5-10 phút do tải models)
docker compose up -d --build fashion-api

# Xem logs realtime (Ctrl+C để thoát)
docker compose logs -f fashion-api
```

Chờ đến khi thấy:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Bước 5: Truy cập

Mở trình duyệt: **http://localhost:8000**

> 🎉 Done! Fashion Agent đang chạy.

---

### � Nạp dữ liệu (Lần đầu tiên)

Sau khi API server đã chạy, cần nạp dữ liệu vào hệ thống.

#### Chuẩn bị dataset

1. Tải dataset từ [Kaggle - Fashion Product Images](https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset) hoặc dataset tự chuẩn bị.
2. Giải nén và đặt ảnh vào folder `images/` trong folder `fashion_agent/`.

#### Bước 1: Ingestion — Kaggle → PostgreSQL + Gemini Enrichment

```bash
# Exec vào container
docker exec -it fashion-api bash

# Nạp dữ liệu Kaggle, sinh caption + detect color bằng Gemini
python -m pre_processing.processing_data
```

> ⚠️ **Lưu ý**: Bước này tốn thời gian vì gọi Gemini API cho từng ảnh (batch 20 items/lần).
> Mỗi ảnh = 2 Gemini calls (1 caption + 1 color detection).

#### Bước 2: Indexing — PostgreSQL → Qdrant + BM25

```bash
# Vẫn trong container fashion-api
python -m indexing.build_index
```

> ⚠️ **Lưu ý**: Lần đầu sẽ tải model FashionSigLIP (~1GB) vào folder `models/`.

#### Kiểm tra dữ liệu đã nạp

```bash
# Kiểm tra Qdrant collections
curl -s http://localhost:6333/collections | python3 -m json.tool

# Kiểm tra PostgreSQL (số items)
docker exec fashion-postgres psql -U fashion_user -d fashion_rag \
  -c "SELECT count(*) FROM fashion_items;"
```

---

### 🖥️ Chạy Local (cho phát triển)

#### Bước 1: Cài dependencies

```bash
cd fashion_agent
pip install -r requirements-docker.txt
```

#### Bước 2: Chạy databases bằng Docker

```bash
docker compose up -d postgres qdrant
```

#### Bước 3: Set biến môi trường

```bash
export PGHOST=localhost PGPORT=5432
export PGDATABASE=fashion_rag PGUSER=fashion_user
export PGPASSWORD=<your_password>
export GEMINI_API_KEY=<your_api_key>
export QDRANT_HOST=localhost QDRANT_PORT=6333
```

#### Bước 4: Chạy server

```bash
python -m api.main
```

---

### 🐳 Docker Commands

```bash
# Xem trạng thái tất cả services
docker compose ps

# Xem logs realtime
docker compose logs -f fashion-api

# Dừng tất cả services
docker compose down

# Dừng + xóa data (reset hoàn toàn)
docker compose down -v

# Rebuild sau khi sửa code
docker compose up -d --build fashion-api

# Chỉ chạy databases (cho dev local)
docker compose up -d postgres qdrant

# Xóa container cũ bị conflict
docker rm -f fashion-qdrant fashion-postgres fashion-api
```

---

### 🔑 Biến môi trường

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `PG_PASSWORD` | ✅ | Mật khẩu PostgreSQL |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `PGDATABASE` | ❌ | Tên database (default: `fashion_rag`) |
| `PGUSER` | ❌ | User PostgreSQL (default: `fashion_user`) |
| `QDRANT_API_KEY` | ❌ | Qdrant auth key (bỏ trống = no auth) |
| `CF_TUNNEL_TOKEN` | ❌ | Cloudflare Tunnel token |
| `DATASET_IMAGES_HOST_PATH` | ❌ | Đường dẫn ảnh Kaggle trên host |

---

### 🏗️ Docker Services

| Service | Image | Port | Vai trò |
|---------|-------|------|---------|
| `postgres` | `postgres:16-alpine` | 5432 | Source of truth cho items + sessions |
| `qdrant` | `qdrant/qdrant:latest` | 6333 | Vector DB cho semantic search |
| `fashion-api` | Custom build | 8000 | FastAPI + Gradio app |
| `cloudflared` | `cloudflare/cloudflared` | — | Public HTTPS tunnel |

---

### 🧪 Kiểm tra Health

```bash
# PostgreSQL
docker exec fashion-postgres pg_isready -U fashion_user -d fashion_rag

# Qdrant
curl -s http://localhost:6333/healthz

# Fashion API
curl -s http://localhost:8000/health

# Qdrant Dashboard (xem collections)
open http://localhost:6333/dashboard
```

---

### 🐛 Troubleshooting

#### Container name conflict

```bash
# Lỗi: "container name is already in use"
docker rm -f fashion-qdrant fashion-postgres fashion-api
docker compose up -d
```

#### Port conflict

```bash
# Kiểm tra port đang dùng
lsof -i :5432  # PostgreSQL
lsof -i :6333  # Qdrant
lsof -i :8000  # Fashion API
```

#### Model download chậm

```bash
# Pre-download FashionSigLIP vào thư mục models/
export HF_HOME=./models
python -c "import open_clip; open_clip.create_model_and_transforms('hf-hub:Marqo/marqo-fashionSigLIP')"
```

#### Qdrant collection trống

```bash
# Chạy lại indexing
docker exec -it fashion-api python -m indexing.build_index
```

#### Gemini API lỗi 429 (rate limit)

```bash
# Giảm batch size trong processing_data.py
# Hoặc chờ 1 phút rồi chạy lại
```

---

## 🤝 Đóng góp code (cho thành viên nhóm)

### Quy trình làm việc

1. **Đọc README này** — hiểu kiến trúc tổng thể
2. **Đọc [docs/development.md](docs/development.md)** — setup môi trường
3. **Chạy thử** — confirm hệ thống hoạt động trên máy bạn
4. **Tạo branch** — `git checkout -b feature/ten-tinh-nang`
5. **Code + test** — đảm bảo không break pipeline hiện tại
6. **Push + tạo PR** — mô tả rõ thay đổi

### File nào sửa cho tính năng nào?

| Muốn làm gì? | Sửa file | Lưu ý |
|---------------|----------|-------|
| Thêm intent mới | `agent/intent_classifier.py` | Cập nhật prompt + `ClassifiedIntent` |
| Sửa logic hỏi clarification | `agent/slot_completeness.py` | Sửa `check_slot_completeness()` threshold |
| Thêm slot mới | `agent/intent_classifier.py` + `slot_completeness.py` | Cập nhật `ExtractedSlots` dataclass + prompt |
| Sửa search pipeline | `search/search_engine.py` | Cẩn thận với thứ tự 7 stages |
| Thay đổi RRF weights | `search/fusion.py` | Tham số: `bm25_weight`, `vec_weight`, `text_vec_weight` |
| Sửa reranker blending | `search/reranker.py` | Tỷ lệ `0.7 × reranker + 0.3 × RRF` |
| Thêm API endpoint | `api/main.py` | Thêm route mới vào FastAPI |
| Sửa Gradio UI | `api/main.py` → `create_gradio_app()` | Gradio components |
| Sửa data ingestion | `pre_processing/processing_data.py` | Ảnh hưởng offline pipeline |
| Sửa vector indexing | `indexing/build_index.py` | Cần rebuild Qdrant sau khi sửa |
| Sửa session/memory | `agent/memory.py` | Ảnh hưởng PostgreSQL schema |

### Conventions

- **Language:** Python 3.11+, type hints (`from __future__ import annotations`)
- **Style:** Dataclass cho data types, singleton pattern cho ML models
- **Config:** Biến môi trường qua `os.getenv()`, có default values
- **Error handling:** Try/except với fallback (nhất là Gemini calls)
- **Logging:** `print()` (chưa migrate sang `logging` module)
- **Import:** Relative imports trong cùng package (`from agent.memory import ...`)

### Lưu ý quan trọng

- **Gemini API key** — mỗi thành viên cần API key riêng (free tại [Google AI Studio](https://aistudio.google.com/apikey))
- **Docker** — databases (PG + Qdrant) LUÔN chạy qua Docker, code Python có thể chạy local
- **Models** — FashionSigLIP (~1GB) và BGE Reranker (~1GB) được cache trong `models/`, download lần đầu
- **Dataset images** — cần mount vào Docker hoặc đặt trong `images/`
- **Singleton pattern** — models load 1 lần rồi cache. Restart server nếu thay đổi model config

---

## 📝 License

Dự án phục vụ mục đích nghiên cứu và học tập.

---

## 👥 Nhóm thực hiện


- **Giảng viên hướng dẫn**: DR.Tran Thanh Tung

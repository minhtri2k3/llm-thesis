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
- [Hướng dẫn cài đặt & chạy](docs/development.md)
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

Xem chi tiết tại 👉 [docs/development.md](docs/development.md)

---

## 📝 License

Dự án phục vụ mục đích nghiên cứu và học tập.

---

## 👤 Tác giả

- **Sinh viên**: Lê Minh Trí
- **MSSV**: [MSSV]
- **Giảng viên hướng dẫn**: [Tên giảng viên]

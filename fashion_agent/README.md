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
2. **Hỏi lại khi mơ hồ** — không đoán mò, hỏi câu hỏi làm rõ
3. **Nhớ sở thích** — lưu trữ preferences qua PostgreSQL sessions
4. **Tự lập kế hoạch** — ReAct loop (Reason → Act → Observe), tối đa 8 vòng
5. **Trả lời tự nhiên** — Gemini tổng hợp câu trả lời + gợi ý phối đồ

### So sánh RAG v1.0 → Agent v2.0

| Tiêu chí | RAG v1.0 | Agent v2.0 |
|----------|----------|------------|
| Xử lý truy vấn | Pipeline cứng 9 bước | ReAct loop tự quyết định |
| Truy vấn mơ hồ | Tìm với thông tin thiếu | Hỏi lại người dùng |
| Ngữ cảnh | Không nhớ giữa các lượt | MemoryAgent lưu sở thích phiên |
| Lưu trữ | CSV cục bộ | PostgreSQL (triển khai server) |
| Từ chối lịch sự | Không có | Phát hiện out-of-scope |
| Kết quả | Danh sách sản phẩm | Sản phẩm + lý luận + gợi ý phối đồ |
| Embedding | FashionCLIP (512-d) | Marqo-FashionSigLIP (768-d) |
| Query Expansion | Không có | Gemini sinh synonym queries |
| Reranker | Không có | BGE Reranker v2-m3 (cross-encoder) |

---

## ✨ Tính năng chính

### 🔍 Hybrid Search Pipeline (7 stages)

```
Query Expansion (Gemini) → BM25 (top-20) + Vector (top-20)
    → Dedup Merge → RRF Fusion → Soft Filter → BGE Rerank → Top-6
```

- **BM25**: Tìm chính xác theo category + màu sắc (`rank_bm25`)
- **Vector Search**: Semantic matching bằng [Marqo-FashionSigLIP](https://huggingface.co/Marqo/marqo-fashionSigLIP) (768-d) trên Qdrant
- **RRF Fusion**: Kết hợp kết quả từ cả hai retriever (k=60, vec_weight=2.5)
- **Soft Filter**: RapidFuzz fuzzy matching trên color + label
- **BGE Reranker**: Cross-encoder reranking cho precision cao

### 🤖 Agent ReAct Loop

```
① Intent Classify (Gemini) 
    → ② Clarification Gate (nếu unclear)
    → ③ Memory Load (preferences từ PostgreSQL)
    → ④ ReAct Loop: Plan → Execute → Observe (max 8 vòng)
    → ⑤ Synthesize (Gemini → answer + styling tips)
```

### 🧠 5 Intent Types

| Intent | Mô tả | Hành động |
|--------|--------|-----------|
| `text_search` | Tìm sản phẩm cụ thể | Tìm kiếm ngay |
| `outfit_request` | Gợi ý trang phục | Tìm + phối đồ |
| `follow_up` | Tham chiếu lượt trước | Dùng ngữ cảnh session |
| `out_of_scope` | Không liên quan thời trang | Từ chối lịch sự |
| `unclear` | Mơ hồ (confidence < 0.6) | Hỏi làm rõ |

### 💾 Session Memory (PostgreSQL)

- Lưu lịch sử query + liked items qua JSONB
- Tự tổng hợp top-3 preferred colors/categories
- Hỗ trợ multi-turn conversation

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                     Gradio UI (:8000)                   │
│                   FastAPI Backend                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐   ┌────────────────┐   ┌──────────────┐  │
│  │  Intent   │──▶│ Clarification  │──▶│   Memory     │  │
│  │Classifier │   │    Gate        │   │   Agent      │  │
│  │ (Gemini)  │   │  (Gemini)      │   │ (PostgreSQL) │  │
│  └──────────┘   └────────────────┘   └──────────────┘  │
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
│  │  Query Expansion → BM25 + Vector ANN    │           │
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
Phase 2 (Runtime): User Query → Agent ReAct → Hybrid Search → LLM Synthesis → Response
```

---

## 🛠️ Tech Stack

| Layer | Technology | Vai trò |
|-------|-----------|---------|
| **LLM** | Gemini 2.5 Flash | Intent, Planning, Synthesis, Caption |
| **Embedding** | Marqo-FashionSigLIP (768-d) | Semantic vector encoding |
| **Vector DB** | Qdrant | ANN search, persistent storage |
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
│   └── main.py              # FastAPI + Gradio UI (376 LOC)
├── agent/
│   ├── fashion_agent.py     # ReAct orchestrator (442 LOC)
│   ├── intent_classifier.py # LLM intent classification (126 LOC)
│   ├── clarification_gate.py # Proactive clarification (110 LOC)
│   └── memory.py            # PostgreSQL session memory (288 LOC)
├── search/
│   ├── search_engine.py     # Hybrid search pipeline (294 LOC)
│   ├── query_expansion.py   # Gemini query expansion (106 LOC)
│   ├── fusion.py            # RRF Fusion (72 LOC)
│   └── reranker.py          # BGE cross-encoder reranker (115 LOC)
├── indexing/
│   └── build_index.py       # FashionSigLIP + Qdrant indexing (470 LOC)
├── pre_processing/
│   └── processing_data.py   # Kaggle → PostgreSQL + Gemini enrichment (698 LOC)
├── documents/
│   ├── Fashion_Agent_Report.pdf
│   └── Fashion_Agent_Report_v2.tex
├── docker-compose.yml       # 4-service stack
├── Dockerfile               # Multi-stage build
├── requirements-docker.txt  # Python dependencies
├── .env.example             # Environment template
└── README.md                # ← Bạn đang đây
```

**Tổng cộng: ~3,097 LOC** (11 Python files production)

---

## 🗺️ Lộ trình phát triển

| Phase | Trạng thái | Nội dung |
|-------|-----------|----------|
| **Phase 1** — RAG v1.0 | ✅ Hoàn thành | Pipeline 9 bước, FashionCLIP, CSV |
| **Phase 2** — Agent v2.0 | ✅ Hoàn thành | ReAct loop, PostgreSQL, FashionSigLIP, Docker |
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

- **Sinh viên**: [Tên sinh viên]
- **MSSV**: [MSSV]
- **Giảng viên hướng dẫn**: [Tên giảng viên]

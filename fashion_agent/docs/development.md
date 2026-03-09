# Fashion Agent RAG — Development Guide

## Yêu cầu hệ thống

- **Docker Desktop** (đã bật)
- **Python 3.11+** (cho dev local)
- **uv** (Python package manager)

---

## Quick Start (3 bước)

### 1. Khởi động databases

```bash
cd qwen_local_rag
docker compose up -d postgres qdrant
```

Kiểm tra healthy:
```bash
docker compose ps
# Cả 2 phải hiện "healthy"
```

### 2. Nạp dữ liệu (chỉ cần chạy 1 lần)

```bash
# Tạo venv + cài dependencies
~/.local/bin/uv venv
~/.local/bin/uv pip install psycopg2-binary tqdm Pillow kagglehub

# Set env vars
export PGHOST=localhost PGPORT=5432
export PGDATABASE=fashion_rag PGUSER=fashion_user
export PGPASSWORD='**REDACTED_DB_PASSWORD**'

# Kiểm tra kết nối
.venv/bin/python pre_processing/processing_data.py doctor

# Tạo tables
.venv/bin/python pre_processing/processing_data.py init-db

# Nạp dữ liệu từ Kaggle (6.5GB download, chạy 1 lần)
.venv/bin/python pre_processing/processing_data.py ingest-kaggle --limit 50
```

### 3. Index vectors + chạy API

```bash
# Cài thêm ML deps
~/.local/bin/uv pip install qdrant-client open-clip-torch transformers \
  huggingface-hub rank-bm25 torch rapidfuzz sentence-transformers \
  accelerate google-generativeai fastapi uvicorn gradio

# Set thêm env vars
export QDRANT_HOST=localhost QDRANT_PORT=6333
export GEMINI_API_KEY=**REDACTED_GEMINI_API_KEY**

# Index dữ liệu vào Qdrant (chạy 1 lần)
.venv/bin/python -m indexing.build_index init
.venv/bin/python -m indexing.build_index build --batch-size 16

# Kiểm tra index
.venv/bin/python -m indexing.build_index status
# → PostgreSQL items: 50, Qdrant vectors: 50

# CHẠY API SERVER
.venv/bin/python -m api.main
```

Mở trình duyệt: **http://localhost:8000** → Gradio Chat UI

---

## Các lệnh hay dùng

### Chạy với Docker (production-like)

```bash
# Chạy 3 services (không cần Cloudflare)
docker compose up -d postgres qdrant fashion-api

# Xem status
docker compose ps

# Xem logs
docker logs fashion-api -f

# Dừng tất cả
docker compose down

# Dừng + xóa data
docker compose down -v
```

### Chạy local (development)

```bash
# Source env vars (mỗi terminal mới cần chạy lại)
export PGHOST=localhost PGPORT=5432 PGDATABASE=fashion_rag
export PGUSER=fashion_user PGPASSWORD='**REDACTED_DB_PASSWORD**'
export QDRANT_HOST=localhost QDRANT_PORT=6333
export GEMINI_API_KEY=**REDACTED_GEMINI_API_KEY**

# Chạy API server (cần PG + Qdrant đang chạy)
.venv/bin/python -m api.main

# Test health
curl http://localhost:8000/health

# Test chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "tìm áo sơ mi trắng"}'
```

### Rebuild Docker image

```bash
docker compose build fashion-api
docker compose up -d fashion-api
```

---

## API Endpoints

| Method | Path | Mô tả |
|--------|------|--------|
| `GET` | `/` | Gradio Chat UI |
| `POST` | `/api/chat` | Agent chat — body: `{"message": "...", "session_id": "..."}` |
| `GET` | `/api/products/{image_id}` | Chi tiết sản phẩm |
| `GET` | `/api/images/{filename}` | Serve ảnh sản phẩm |
| `GET` | `/health` | Health check (PG + Qdrant) |
| `GET` | `/docs` | Swagger UI (auto-generated) |

---

## Kiến trúc Pipeline

```
User Query
  → Intent Classifier (Gemini)
  → Clarification Gate (nếu query mơ hồ)
  → Hybrid Search:
      BM25 (keyword, top-20) + Vector ANN (FashionSigLIP, top-20)
      → RRF Fusion (k=60)
      → Soft Filter (RapidFuzz ≥60)
      → BGE Reranker (top-6)
  → Gemini Synthesis (Vietnamese response)
  → Session Memory (PostgreSQL)
```

---

## Lưu ý

- **Lần đầu chạy** sẽ download ~4GB models (FashionSigLIP 813MB + BGE Reranker 2.27GB). Models cache tại `./models/`
- **Docker API container** cũng cần download models lần đầu — request đầu sẽ chậm ~2-3 phút
- **RAM:** Cần ~8-10GB RAM khi chạy đầy đủ pipeline (2 models loaded)
- **MPS:** Tự động dùng Apple Silicon GPU nếu chạy local trên Mac

# 🔧 Development Guide — Fashion Agent

Hướng dẫn từng bước để **clone → cài đặt → chạy** hệ thống Fashion Agent RAG Pipeline.

---

## Yêu cầu hệ thống

| Yêu cầu | Phiên bản |
|----------|-----------|
| Docker + Docker Compose | v24+ |
| Python (nếu dev local) | 3.11+ |
| Git | 2.39+ |
| RAM | ≥8GB (khuyến nghị 16GB) |
| Disk | ~5GB (models + images) |
| Gemini API Key | [Lấy tại đây](https://aistudio.google.com/apikey) |

---

## 🚀 Quick Start — Từ đầu đến chạy (5 bước)

### Bước 1: Clone repository

```bash
git clone https://github.com/minhtri2k3/llm-thesis.git
cd llm-thesis/fashion_agent
```

### Bước 2: Cấu hình môi trường

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

### Bước 3: Khởi động databases

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

### Bước 4: Build và chạy API

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

### Bước 5: Truy cập

Mở trình duyệt: **http://localhost:8000**

> 🎉 Done! Fashion Agent đang chạy.

---

## 📦 Nạp dữ liệu (Lần đầu tiên)

Sau khi API server đã chạy, cần nạp dữ liệu vào hệ thống.

### Chuẩn bị dataset

1. Tải dataset từ [Kaggle - Fashion Product Images](https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset) hoặc dataset tự chuẩn bị.
2. Giải nén và đặt ảnh vào folder `images/` trong folder `fashion_agent/`.

### Bước 1: Ingestion — Kaggle → PostgreSQL + Gemini Enrichment

```bash
# Exec vào container
docker exec -it fashion-api bash

# Nạp dữ liệu Kaggle, sinh caption + detect color bằng Gemini
python -m pre_processing.processing_data
```

> ⚠️ **Lưu ý**: Bước này tốn thời gian vì gọi Gemini API cho từng ảnh (batch 20 items/lần).
> Mỗi ảnh = 2 Gemini calls (1 caption + 1 color detection).

### Bước 2: Indexing — PostgreSQL → Qdrant + BM25

```bash
# Vẫn trong container fashion-api
python -m indexing.build_index
```

> ⚠️ **Lưu ý**: Lần đầu sẽ tải model FashionSigLIP (~1GB) vào folder `models/`.

### Kiểm tra dữ liệu đã nạp

```bash
# Kiểm tra Qdrant collections
curl -s http://localhost:6333/collections | python3 -m json.tool

# Kiểm tra PostgreSQL (số items)
docker exec fashion-postgres psql -U fashion_user -d fashion_rag \
  -c "SELECT count(*) FROM fashion_items;"
```

---

## 🖥️ Chạy Local (cho phát triển)

### Bước 1: Cài dependencies

```bash
cd fashion_agent
pip install -r requirements-docker.txt
```

### Bước 2: Chạy databases bằng Docker

```bash
docker compose up -d postgres qdrant
```

### Bước 3: Set biến môi trường

```bash
export PGHOST=localhost PGPORT=5432
export PGDATABASE=fashion_rag PGUSER=fashion_user
export PGPASSWORD=<your_password>
export GEMINI_API_KEY=<your_api_key>
export QDRANT_HOST=localhost QDRANT_PORT=6333
```

### Bước 4: Chạy server

```bash
python -m api.main
```

---

## 🐳 Docker Commands

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

## 🔑 Biến môi trường

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

## 🏗️ Docker Services

| Service | Image | Port | Vai trò |
|---------|-------|------|---------|
| `postgres` | `postgres:16-alpine` | 5432 | Source of truth cho items + sessions |
| `qdrant` | `qdrant/qdrant:latest` | 6333 | Vector DB cho semantic search |
| `fashion-api` | Custom build | 8000 | FastAPI + Gradio app |
| `cloudflared` | `cloudflare/cloudflared` | — | Public HTTPS tunnel |

---

## 🧪 Kiểm tra Health

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

## 🧩 Kiến trúc module

```
agent/
├── intent_classifier.py     # 1 LLM call → intent + 6 slots
├── slot_completeness.py     # check_slot_completeness, merge_slots
├── clarification_gate.py    # generic clarification (cho unclear/outfit)
├── fashion_agent.py         # ReAct orchestrator + slot flow
└── memory.py                # PostgreSQL session management

search/
├── search_engine.py         # 7-stage hybrid pipeline
├── query_expansion.py       # Gemini synonym expansion
├── fusion.py                # RRF 3-source fusion
└── reranker.py              # BGE cross-encoder

indexing/
└── build_index.py           # SigLIP encode → Qdrant + BM25

pre_processing/
└── processing_data.py       # Kaggle ingestion + Gemini enrichment
```

---

## 🐛 Troubleshooting

### Container name conflict

```bash
# Lỗi: "container name is already in use"
docker rm -f fashion-qdrant fashion-postgres fashion-api
docker compose up -d
```

### Port conflict

```bash
# Kiểm tra port đang dùng
lsof -i :5432  # PostgreSQL
lsof -i :6333  # Qdrant
lsof -i :8000  # Fashion API
```

### Model download chậm

```bash
# Pre-download FashionSigLIP vào thư mục models/
export HF_HOME=./models
python -c "import open_clip; open_clip.create_model_and_transforms('hf-hub:Marqo/marqo-fashionSigLIP')"
```

### Qdrant collection trống

```bash
# Chạy lại indexing
docker exec -it fashion-api python -m indexing.build_index
```

### Gemini API lỗi 429 (rate limit)

```bash
# Giảm batch size trong processing_data.py
# Hoặc chờ 1 phút rồi chạy lại
```

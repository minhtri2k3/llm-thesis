# 🔧 Development Guide — Fashion Agent

## Yêu cầu hệ thống

| Yêu cầu | Phiên bản |
|----------|-----------|
| Docker + Docker Compose | v24+ |
| Python (nếu dev local) | 3.11+ |
| RAM | ≥8GB (khuyến nghị 16GB) |
| Disk | ~5GB (models + images) |
| Gemini API Key | [Lấy tại đây](https://aistudio.google.com/apikey) |

---

## 🚀 Cách 1: Chạy bằng Docker (Khuyến nghị)

### Bước 1: Cấu hình môi trường

```bash
cd fashion_agent

# Copy file .env mẫu
cp .env.example .env

# Sửa .env: điền GEMINI_API_KEY và PG_PASSWORD
```

### Bước 2: Khởi động databases

```bash
# Khởi động PostgreSQL + Qdrant
docker compose up -d postgres qdrant

# Kiểm tra trạng thái (chờ cả hai healthy)
docker compose ps
```

### Bước 3: Build và chạy API

```bash
# Build + chạy Fashion API (lần đầu ~5-10 phút)
docker compose up -d --build fashion-api

# Xem logs realtime
docker compose logs -f fashion-api
```

### Bước 4: Truy cập

Mở trình duyệt tại: **http://localhost:8000**

---

## 🖥️ Cách 2: Chạy Local (cho dev)

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

## 📦 Nạp dữ liệu (Lần đầu tiên)

Sau khi databases đã chạy, cần nạp dữ liệu vào hệ thống:

### Bước 1: Ingestion — Kaggle → PostgreSQL + Gemini Enrichment

```bash
# Nạp dữ liệu Kaggle, sinh caption + detect color bằng Gemini
python -m pre_processing.processing_data
```

> ⚠️ **Lưu ý**: Bước này tốn thời gian vì gọi Gemini API cho từng ảnh (batch 20 items/lần).

### Bước 2: Indexing — PostgreSQL → Qdrant + BM25

```bash
# Encode ảnh bằng FashionSigLIP → upsert Qdrant + build BM25
python -m indexing.build_index
```

> ⚠️ **Lưu ý**: Lần đầu sẽ tải model FashionSigLIP (~1GB).

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
python -m indexing.build_index
```

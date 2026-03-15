# Fashion Agent — Development Guide

## Yêu cầu hệ thống

| Yêu cầu | Chi tiết |
|----------|----------|
| Docker Desktop | Đã cài và **đang chạy** |
| RAM | ≥ 16GB (models SigLIP + BGE chiếm ~4GB) |
| Dataset ảnh | Kaggle `agrigorev/clothing-dataset-full` |
| Gemini API Key | Dùng cho agent synthesis + pre-processing |

---

## Khởi động nhanh (đã có data)

Khi đã từng chạy dự án trước đó và data vẫn còn trong Docker volumes:

```bash
cd fashion_agent

# Khởi động tất cả services
docker compose up -d

# Theo dõi tiến trình load models
docker logs -f fashion-api

# Khi thấy "Uvicorn running on 0.0.0.0:8000" → sẵn sàng
# Ctrl+C để thoát logs

# Mở UI
open http://localhost:8000
```

### Các giai đoạn khởi động API

Khi xem logs (`docker logs -f fashion-api`), bạn sẽ thấy:

```
1. "Memory tables initialized."           (~2s)    — Tạo bảng session PostgreSQL
2. "Loading FashionSigLIP model..."        (~30-60s) — Tải model SigLIP vào RAM
3. "Loading BGE Reranker..."              (~15-30s) — Tải model reranker
4. "BGE Reranker loaded successfully."     ✅        — SẴN SÀNG
5. "Uvicorn running on 0.0.0.0:8000"      🌐        — UI có thể truy cập
```

> Tổng: ~1-2 phút. Nhanh hơn nếu models đã cache trong `./models/`.

---

## Chạy từ đầu (chưa có data)

Khi clone repo mới hoặc đã xóa Docker volumes.

> ⏱️ **Tổng thời gian: ~2-4 giờ** (chủ yếu bước 4 và 5)

### Bước 1: Cấu hình `.env`

```bash
cp .env.example .env
```

Sửa các giá trị trong `.env`:

```env
GEMINI_API_KEY=<your-gemini-api-key>
PG_PASSWORD=<your-password>
PGPASSWORD=<same-password>
DATASET_IMAGES_DIR=<path-to-kaggle-images>
```

### Bước 2: Tải dataset

```bash
# Qua Kaggle CLI
kaggle datasets download -d agrigorev/clothing-dataset-full

# Hoặc tải thủ công từ https://www.kaggle.com/datasets/agrigorev/clothing-dataset-full
```

### Bước 3: Khởi động databases

```bash
docker compose up -d postgres qdrant

# Kiểm tra healthy
docker compose ps
```

### Bước 4: Pre-processing (enrichment bằng Gemini)

```bash
uv run python pre_processing/processing_data.py
```

- ⏱️ **Rất lâu** — gọi Gemini API cho ~5000 items
- Output: bảng `fashion_item_enrichment` trong PostgreSQL
- Tạo caption + color cho mỗi sản phẩm

### Bước 5: Build index (embeddings → Qdrant)

```bash
uv run python indexing/build_index.py
```

- ⏱️ **Lâu** — encode ảnh + text bằng SigLIP cho ~5000 items
- Output: vectors trong Qdrant + BM25 index

### Bước 6: Khởi động toàn bộ stack

```bash
docker compose up -d

# Theo dõi startup
docker logs -f fashion-api
```

- Lần đầu build Docker image mất ~5-10 phút (tải models)

### Bước 7: Truy cập UI

```
🌐  http://localhost:8000
```

---

## Kiến trúc services

```
┌────────────────────────────────────────────────┐
│               docker compose up -d             │
├────────────────────────────────────────────────┤
│                                                │
│  ┌─────────────┐       ┌──────────────┐       │
│  │  postgres    │       │    qdrant    │       │
│  │  :5432       │       │    :6333    │       │
│  │  fashion_rag │       │   vectors   │       │
│  │  + enrichment│       │   + BM25    │       │
│  └──────┬───────┘       └──────┬──────┘       │
│         └──────────┬───────────┘              │
│                    │                           │
│           ┌────────▼─────────┐                │
│           │   fashion-api    │                │
│           │     :8000        │                │
│           │  FastAPI+Gradio  │                │
│           │  SigLIP + BGE +  │                │
│           │  Gemini Agent    │                │
│           └────────┬─────────┘                │
│                    │                           │
│           ┌────────▼─────────┐                │
│           │   cloudflared    │  (optional)    │
│           │  Public tunnel   │                │
│           └──────────────────┘                │
│                                                │
└────────────────────────────────────────────────┘
```

---

## Lệnh thường dùng

### Docker

| Mục đích | Lệnh |
|----------|-------|
| Khởi động tất cả | `docker compose up -d` |
| Khởi động + xem logs | `docker compose up -d && docker logs -f fashion-api` |
| Chạy foreground (thấy hết) | `docker compose up` |
| Xem logs API | `docker logs -f fashion-api` |
| Xem trạng thái | `docker compose ps` |
| Health check | `curl localhost:8000/health` |
| Dừng tất cả (giữ data) | `docker compose down` |
| Dừng + **XÓA data** | `docker compose down -v` ⚠️ |

### Rebuild sau khi sửa code

```bash
# Rebuild chỉ API container
docker compose build fashion-api

# Restart API
docker compose up -d fashion-api

# Hoặc 1 lệnh
docker compose build fashion-api && docker compose up -d fashion-api
```

### Cập nhật text index (không cần re-index ảnh)

```bash
uv run python indexing/update_text_index.py
```

### Chạy tests

```bash
# Test search accuracy
uv run python test_search.py

# Test full agent pipeline
uv run python test_chat.py
```

---

## Lưu ý quan trọng

> ⚠️ **`docker compose down -v`** sẽ **xóa toàn bộ** PostgreSQL data + Qdrant vectors.
> Bạn sẽ phải chạy lại bước 4 + 5 (tốn vài giờ)!
> Chỉ dùng `docker compose down` (không có `-v`) nếu muốn giữ data.

> 💡 **Models cache:** Lần đầu chạy, SigLIP và BGE Reranker sẽ tải từ HuggingFace
> và cache vào `./models/`. Các lần sau sẽ nhanh hơn nhiều.

> 💡 **DATASET_IMAGES_DIR:** Biến này trỏ đến thư mục ảnh dataset trên host machine.
> Docker mount thư mục này vào `/app/dataset_images/` bên trong container.

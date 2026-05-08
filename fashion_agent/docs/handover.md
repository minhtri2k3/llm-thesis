# 📦 Hướng dẫn chuyển giao — Fashion Agent RAG Pipeline

> **Tài liệu này dành cho người nhận** để chạy được hệ thống Fashion Agent trên máy mới.
> Mọi bước preprocessing và embedding đã hoàn tất. Bạn chỉ cần import dữ liệu và bật Docker.

---

## 📋 Danh sách file cần nhận

Bạn cần nhận **4 thứ** từ người chuyển giao:

| # | Tên file | Kích thước | Mô tả |
|---|----------|-----------|-------|
| 1 | **Source code** (Git repo) | — | Clone từ GitHub |
| 2 | **`.env`** | ~1 KB | Biến môi trường, chứa API keys |
| 3 | **`pgdata_backup.tar.gz`** | ~69 MB | PostgreSQL data (metadata sản phẩm) |
| 4 | **`qdrant_backup.tar.gz`** | ~59 MB | Qdrant vectors (embeddings đã index) |
| 5 | **Ảnh dataset** (tuỳ chọn) | ~165 MB | Ảnh sản phẩm từ Kaggle |

---

## Yêu cầu hệ thống

- **Docker Desktop** (đã cài và đang chạy)
- **RAM**: tối thiểu 8 GB (khuyến nghị 16 GB)
- **Ổ cứng trống**: ~5 GB (cho models tự tải lần đầu)
- **Internet**: cần cho lần chạy đầu tiên (tải HuggingFace models ~3.7 GB)

---

## Hướng dẫn từng bước

### Bước 1: Clone source code

```bash
git clone https://github.com/minhtri2k3/llm-thesis.git
cd llm-thesis/fashion_agent
```

### Bước 2: Tạo file `.env`

Tạo file `.env` từ template:

```bash
cp .env.example .env ( tôi gửi m riêng )
```

Mở file `.env` và điền các giá trị sau:

```ini
# ── BẮT BUỘC ──────────────────────────────────────────────
# PostgreSQL password (phải khớp với data đã backup)
PG_PASSWORD=<nhận từ người chuyển giao> ( này nằm trong .evn rồi )

# Gemini API Key (lấy tại https://aistudio.google.com/apikey)
GEMINI_API_KEY=<API key của bạn> ( này trong .evn rồi ) 

# ── TUỲ CHỌN ──────────────────────────────────────────────
# Path đến folder ảnh dataset trên máy bạn
DATASET_IMAGES_HOST_PATH=<path đến folder ảnh> ( lấy về trỏ qua thôi )

# Cloudflare Tunnel (bỏ qua nếu không cần public access)
CF_TUNNEL_TOKEN=placeholder ( như trong .env)
```

> ⚠️ **Quan trọng**: `PG_PASSWORD` phải đúng giá trị mà người chuyển giao cung cấp,
> vì PostgreSQL data backup đã được tạo với password này.

### Bước 3: Import Docker Volumes

Đặt 2 file backup (`pgdata_backup.tar.gz` và `qdrant_backup.tar.gz`) vào thư mục `fashion_agent/`, rồi chạy:

```bash
# Tạo volume cho PostgreSQL và import data
docker volume create fashion_agent_pgdata
docker run --rm \
  -v fashion_agent_pgdata:/data \
  -v "$(pwd)":/backup \
  alpine tar xzf /backup/pgdata_backup.tar.gz -C /data

# Tạo volume cho Qdrant và import data
docker volume create fashion_agent_qdrant_data
docker run --rm \
  -v fashion_agent_qdrant_data:/data \
  -v "$(pwd)":/backup \
  alpine tar xzf /backup/qdrant_backup.tar.gz -C /data
```

Kiểm tra volumes đã được tạo:

```bash
docker volume ls --filter name=fashion_agent
```

Kết quả mong đợi:

```
DRIVER    VOLUME NAME
local     fashion_agent_pgdata
local     fashion_agent_qdrant_data
```

### Bước 4: Chuẩn bị ảnh dataset

**Option A — Nhận ảnh trực tiếp:**

Giải nén ảnh vào một folder, rồi trỏ path trong `.env`:

```ini
DATASET_IMAGES_HOST_PATH=/path/to/your/images_folder
```

**Option B — Tải từ Kaggle:**

```bash
pip install kagglehub
python -c "import kagglehub; path = kagglehub.dataset_download('agrigorev/clothing-dataset-full'); print(path)"
```

Rồi set path output vào `.env`:

```ini
DATASET_IMAGES_HOST_PATH=<path-output-ở-trên>/images_compressed
```

**Option C — Bỏ qua:**

Nếu không set `DATASET_IMAGES_HOST_PATH`, Docker sẽ dùng default `./images` (folder rỗng). Hệ thống vẫn chạy nhưng không hiển thị ảnh sản phẩm.

### Bước 5: Khởi động hệ thống

```bash
# Nếu KHÔNG cần Cloudflare Tunnel (chạy local):
docker compose up -d postgres qdrant fashion-api

# Nếu CẦN Cloudflare Tunnel (public access):
docker compose up -d
```

### Bước 6: Kiểm tra hệ thống

```bash
# Xem trạng thái tất cả services
docker compose ps
```

Kết quả mong đợi (chờ ~30-60 giây):

```
NAME                 STATUS
fashion-postgres     Up (healthy)
fashion-qdrant       Up (healthy)
fashion-api          Up
```

Mở trình duyệt tại: **http://localhost:8000**

> 💡 **Lần chạy đầu tiên** fashion-api sẽ tốn thêm ~5-10 phút để tải models
> từ HuggingFace (~3.7 GB). Theo dõi tiến trình:
> ```bash
> docker compose logs -f fashion-api
> ```

---

## ⚠️ Những điều NGHIÊM CẤM

```
❌ TUYỆT ĐỐI KHÔNG:   docker compose down -v
                        (flag -v sẽ XÓA TOÀN BỘ volumes = mất hết data!)

❌ KHÔNG:               docker volume rm fashion_agent_pgdata
❌ KHÔNG:               docker volume rm fashion_agent_qdrant_data
```

---

## ✅ Các lệnh an toàn

```bash
# Tắt hệ thống (giữ data)
docker compose stop

# Bật lại hệ thống
docker compose up -d

# Xem logs
docker compose logs -f fashion-api

# Restart 1 service
docker compose restart fashion-api

# Rebuild API sau khi sửa code
docker compose up -d --build fashion-api
```

---

## 🧪 Cohort LLM Evaluation Study (4-Gemini)

The cohort study compares Indigo (gemini-2.5-flash) / Crimson (gemini-2.5-pro) /
Emerald (gemini-3.1-flash-lite) / Amber (gemini-3.1-pro-preview) across testers.

**Toggle**: set `ENABLE_COHORT_STUDY=true` in `.env`, then `docker compose restart fashion-api`.
Default is `false` — when off, the system behaves identically to the pre-cohort version.

**Data preservation**: schema changes are *additive only* — `ALTER TABLE … ADD COLUMN
IF NOT EXISTS …`. Pre-cohort sessions and rows stay queryable; new columns
(`study_group`, `agent_codename`, `latency_ms`, `intent_latency_ms`,
`synthesis_latency_ms`) default to NULL/0 on legacy rows. **No DROP COLUMN is
performed by this change.**

**Admin dashboard**: `GET /api/analytics/cohort` (requires `X-Admin-Key`) returns the
4-cell summary plus the codename↔model mapping. The Flutter Professor View shows
this as the "Cohort LLM Evaluation" card. Returns HTTP 503 when the flag is off.

**Filter analyses**: cohort-only data is `WHERE study_group IS NOT NULL` on
`user_sessions`. Pre-study legacy data is `WHERE study_group IS NULL`.

---

## 🔧 Xử lý sự cố

### Lỗi: `PG_PASSWORD is required`

→ File `.env` thiếu biến `PG_PASSWORD`. Kiểm tra lại file `.env`.

### Lỗi: `GEMINI_API_KEY is required`

→ File `.env` thiếu biến `GEMINI_API_KEY`. Đăng ký tại [Google AI Studio](https://aistudio.google.com/apikey).

### Lỗi: `password authentication failed for user`

→ `PG_PASSWORD` trong `.env` không khớp với password trong PostgreSQL volume.
Hỏi lại người chuyển giao password chính xác.

### Lỗi: Container "already in use"

```bash
docker rm -f fashion-postgres fashion-qdrant fashion-api fashion-cloudflared
docker compose up -d
```

### fashion-api thoát ngay sau khi start

```bash
docker compose logs fashion-api
```

Thường do thiếu `GEMINI_API_KEY` hoặc model chưa download xong.

### Port đã bị chiếm (5432, 6333, 8000)

Tìm process chiếm port:

```bash
lsof -i :5432    # PostgreSQL
lsof -i :6333    # Qdrant
lsof -i :8000    # Fashion API
```

Tắt process đó, hoặc đổi port trong `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"   # Đổi host port thành 5433
```

---

## 📁 Cấu trúc thư mục tham khảo

```
fashion_agent/
├── .env                    ← Biến môi trường (KHÔNG commit, gửi riêng)
├── .env.example            ← Template cho .env
├── docker-compose.yml      ← Cấu hình Docker stack
├── Dockerfile              ← Build image cho fashion-api
├── requirements-docker.txt ← Python dependencies
├── api/                    ← FastAPI + Gradio UI
├── agent/                  ← ReAct Agent logic
├── search/                 ← Hybrid search engine
├── models/                 ← HuggingFace model cache (tự tải)
├── images/                 ← Local images (có thể rỗng)
└── docs/
    ├── development.md      ← Hướng dẫn development
    └── handover.md         ← File này
```

---

## 🏗️ Kiến trúc hệ thống

```
                    ┌──────────────────┐
                    │   Trình duyệt    │
                    │ localhost:8000    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   fashion-api    │
                    │  FastAPI+Gradio  │
                    │   (port 8000)    │
                    └──┬──────────┬────┘
                       │          │
              ┌────────▼──┐  ┌───▼────────┐
              │ PostgreSQL │  │   Qdrant   │
              │ (port 5432)│  │ (port 6333)│
              │ metadata   │  │  vectors   │
              └──────┬─────┘  └─────┬──────┘
                     │              │
              Named Volume    Named Volume
              pgdata          qdrant_data
              ⚠️ KHÔNG XÓA    ⚠️ KHÔNG XÓA
```

---

*Tài liệu tạo ngày 19/03/2026 — Fashion Agent RAG Pipeline v1.0*

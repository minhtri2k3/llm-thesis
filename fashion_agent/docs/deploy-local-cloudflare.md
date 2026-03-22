# 🚀 Deploy Fashion Agent — Local + Public Access (Cloudflare Tunnel)

> **Mục tiêu**: Chạy toàn bộ stack trên máy này và expose public qua Cloudflare Tunnel.  
> **Thời gian**: ~10-15 phút (nếu đã có backup volumes)  
> **Yêu cầu**: Docker Desktop đang chạy, đã có `pgdata_backup.tar.gz` + `qdrant_backup.tar.gz` + `.env`

---

## 📋 Tổng quan flow

```
[Bước 1] Chuẩn bị Cloudflare Tunnel
[Bước 2] Cập nhật .env với CF_TUNNEL_TOKEN
[Bước 3] Import Docker Volumes (từ backup)
[Bước 4] Khởi động toàn bộ stack
[Bước 5] Verify hệ thống
[Bước 6] Truy cập qua URL công khai
```

---

## 🔑 Bước 1: Chuẩn bị Cloudflare Tunnel

### 1a. Đăng ký / đăng nhập Cloudflare

Vào: https://dash.cloudflare.com  
(Cần có tài khoản Cloudflare — miễn phí)

### 1b. Tạo Tunnel mới

1. Vào **Zero Trust** → **Networks** → **Tunnels**
2. Click **"Add a tunnel"**
3. Chọn **"Cloudflared"**
4. Đặt tên tunnel (ví dụ: `fashion-agent`)
5. Copy **Tunnel Token** hiện ra  
   → Token có dạng: `eyJhIjoiYWJj...` (rất dài)

### 1c. Cấu hình Public Hostname trong tunnel

Trong trang cấu hình tunnel, thêm một **Public Hostname**:

| Field | Giá trị |
|-------|---------|
| Subdomain | `fashion` (hoặc tên tùy ý) |
| Domain | Domain bạn đã add vào Cloudflare |
| Type | `HTTP` |
| URL | `fashion-api:8000` |

> 💡 Nếu không có domain: Cloudflare cho phép dùng subdomain miễn phí `*.trycloudflare.com` — xem phần **Không có domain** bên dưới.

---

## ⚙️ Bước 2: Cập nhật file `.env`

```bash
cd /Users/tringuyen/llm-thesis/fashion_agent
```

Mở file `.env` và điền `CF_TUNNEL_TOKEN`:

```bash
# Xem nội dung .env hiện tại
cat .env
```

Sửa dòng `CF_TUNNEL_TOKEN`:

```ini
CF_TUNNEL_TOKEN=<paste token từ Cloudflare Dashboard vào đây>
```

> ⚠️ Xóa chữ `placeholder` và thay bằng token thật. Token KHÔNG có dấu ngoặc kép.

---

## 📦 Bước 3: Import Docker Volumes từ backup

> ⚠️ **Chỉ cần chạy một lần.** Nếu volumes đã tồn tại, bỏ qua bước này.

```bash
cd /Users/tringuyen/llm-thesis/fashion_agent
```

### Import PostgreSQL volume

```bash
docker volume create fashion_agent_pgdata

docker run --rm \
  -v fashion_agent_pgdata:/data \
  -v "$(pwd)":/backup \
  alpine tar xzf /backup/pgdata_backup.tar.gz -C /data
```

### Import Qdrant volume

```bash
docker volume create fashion_agent_qdrant_data

docker run --rm \
  -v fashion_agent_qdrant_data:/data \
  -v "$(pwd)":/backup \
  alpine tar xzf /backup/qdrant_backup.tar.gz -C /data
```

### Xác nhận volumes đã tạo thành công

```bash
docker volume ls --filter name=fashion_agent
```

Kết quả mong đợi:

```
DRIVER    VOLUME NAME
local     fashion_agent_pgdata
local     fashion_agent_qdrant_data
```

---

## 🐳 Bước 4: Khởi động toàn bộ stack

```bash
cd /Users/tringuyen/llm-thesis/fashion_agent

docker compose up -d
```

Lệnh này khởi động **4 services**: `postgres`, `qdrant`, `fashion-api`, `cloudflared`.

### Theo dõi quá trình startup

```bash
# Xem trạng thái tất cả containers
docker compose ps

# Theo dõi logs API (quan trọng nhất)
docker compose logs -f fashion-api
```

### Các giai đoạn startup của `fashion-api`

```
[  ~2s] "Memory tables initialized."       — Kết nối PostgreSQL OK
[ ~60s] "Loading FashionSigLIP model..."   — Tải model ảnh (~2GB)
[ ~30s] "Loading BGE Reranker..."          — Tải model reranking
[~120s] "BGE Reranker loaded."             ✅ Models sẵn sàng
[~125s] "Uvicorn running on 0.0.0.0:8000" 🌐 UI có thể truy cập
```

> ⏱️ **Lần đầu**: ~5-10 phút (tải models từ HuggingFace ~3.7 GB)  
> ⏱️ **Lần sau**: ~2-3 phút (models đã cache trong `./models/`)

---

## ✅ Bước 5: Verify hệ thống

### Kiểm tra tất cả containers đang healthy

```bash
docker compose ps
```

Kết quả mong đợi:

```
NAME                   STATUS
fashion-postgres       Up (healthy)
fashion-qdrant         Up (healthy)
fashion-api            Up
fashion-cloudflared    Up
```

### Health check API

```bash
curl -sf http://localhost:8000/health && echo "✅ API OK" || echo "❌ API chưa sẵn sàng"
```

### Kiểm tra Cloudflare Tunnel đang kết nối

```bash
docker compose logs cloudflared | tail -20
```

Tìm dòng tương tự:

```
INF Connection ... registered
INF Registered tunnel connection connIndex=0
```

---

## 🌐 Bước 6: Truy cập

### Local access

```
http://localhost:8000
```

### Public access (qua Cloudflare Tunnel)

```
https://fashion.<your-domain>.com
```

> URL public lấy từ **Cloudflare Dashboard → Zero Trust → Tunnels → Public Hostnames**

---

## 🆓 Không có domain? Dùng Quick Tunnel (tạm thời)

Nếu chỉ muốn test public access nhanh mà không cần domain:

```bash
# Chạy cloudflared một lần để lấy URL tạm thời
docker run --rm cloudflare/cloudflared:latest tunnel --url http://host.docker.internal:8000
```

Kết quả: URL dạng `https://random-name.trycloudflare.com` — miễn phí, không cần đăng nhập.

> ⚠️ URL này thay đổi mỗi lần chạy và chỉ tồn tại khi lệnh đang chạy.

---

## 🔧 Lệnh vận hành hàng ngày

```bash
# Bật hệ thống
docker compose up -d

# Tắt hệ thống (GIỮ data)
docker compose stop

# Xem logs realtime
docker compose logs -f fashion-api

# Xem trạng thái
docker compose ps

# Restart API sau khi sửa code
docker compose build fashion-api && docker compose up -d fashion-api

# Check health
curl localhost:8000/health
```

---

## ⚠️ Cảnh báo quan trọng

```
❌ TUYỆT ĐỐI KHÔNG:
    docker compose down -v
    (flag -v XÓA TOÀN BỘ volumes = mất hết PostgreSQL + Qdrant data!)

✅ AN TOÀN:
    docker compose down      (tắt containers, GIỮ volumes)
    docker compose stop      (suspend, GIỮ volumes)
    docker compose restart   (restart containers, GIỮ volumes)
```

---

## 🛠️ Xử lý sự cố

### Cloudflared không kết nối được

```bash
# Kiểm tra logs
docker compose logs cloudflared

# Thử restart
docker compose restart cloudflared
```

Nguyên nhân thường gặp: `CF_TUNNEL_TOKEN` sai hoặc tunnel đã bị xóa trên Dashboard.

### API không start (exit ngay)

```bash
docker compose logs fashion-api
```

Thường do: thiếu `GEMINI_API_KEY`, hoặc PostgreSQL chưa healthy.

### Port bị chiếm (5432, 6333, 8000)

```bash
lsof -i :8000   # Tìm process chiếm port 8000
lsof -i :5432   # Tìm process chiếm port 5432
lsof -i :6333   # Tìm process chiếm port 6333
```

Kill process đó hoặc đổi port trong `docker-compose.yml`.

### Volumes chưa import → không có data

```bash
# Xem volumes hiện có
docker volume ls --filter name=fashion_agent

# Nếu thiếu → quay lại Bước 3
```

---

## 📐 Kiến trúc khi chạy đầy đủ

```
Internet
   │
   ▼
Cloudflare Edge (HTTPS)
   │
   ▼
cloudflared container ──────────────────────────────────┐
   │                                                    │
   │  (Tunnel encrypted)                                │
   ▼                                                    │
fashion-api :8000  ◄────────────────────────────────────┘
   │         │
   ▼         ▼
PostgreSQL  Qdrant
  :5432      :6333
(metadata) (vectors)
```

Người dùng bên ngoài truy cập qua HTTPS → Cloudflare → Tunnel → `fashion-api` trên máy bạn. Không cần mở port router, không cần IP tĩnh.

---

*Tài liệu tạo ngày 22/03/2026 — Fashion Agent RAG Pipeline*

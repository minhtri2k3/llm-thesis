# 🚀 Fashion Agent: MacBook → Windows Migration Guide

> **Mục tiêu**: Chuyển toàn bộ dữ liệu đã xử lý (PostgreSQL + Qdrant + ảnh) từ MacBook
> sang Windows để self-host, **KHÔNG cần chạy lại pre-processing** (tiết kiệm ~14 giờ + API token).

---

## 📋 Tổng quan

```
Thời gian dự kiến: ~1 giờ (tổng)
Token Gemini tiết kiệm: TOÀN BỘ (không cần chạy lại caption/color)
Dung lượng transfer: 1-5 GB (qua USB)
```

```
┌──────────────────────────────────────────────────────────────────┐
│                         MACBOOK                                  │
│                                                                  │
│  1. pg_dump → fashion_rag_dump.sql         (~5-20 MB)           │
│  2. Qdrant snapshot → fashion_products.snapshot (~50-500 MB)     │
│  3. images/ → images.tar.gz               (~500 MB - 3 GB)     │
│                                                                  │
│  Tổng: 1-4 GB → copy vào USB              ←── PHẦN A            │
└────────────────────────┬─────────────────────────────────────────┘
                         │ USB drive
┌────────────────────────▼─────────────────────────────────────────┐
│                        WINDOWS                                   │
│                                                                  │
│  1. Cài Docker Desktop (hoặc fix WSL)                            │
│  2. Extract images → fashion_agent/images/                       │
│  3. docker compose up -d postgres qdrant                         │
│  4. Import SQL dump → PostgreSQL                                 │
│  5. Fix image paths trong PostgreSQL                             │
│  6. Recover Qdrant snapshot                                      │
│  7. Fix image paths trong Qdrant                                 │
│  8. docker compose up -d (full stack)                            │
│  9. Test: http://localhost:8000             ←── PHẦN B            │
└──────────────────────────────────────────────────────────────────┘
```

---

# PHẦN A — Thực hiện trên MacBook

> ⏱️ Thời gian: ~20 phút

## Bước A.0: Kiểm tra Docker đang chạy

```bash
# Mở Terminal trên Mac
docker ps
```

Kết quả mong đợi — 3 container đang chạy:
```
CONTAINER ID   IMAGE                  ... STATUS          NAMES
abc123         postgres:16-alpine     ... Up (healthy)    fashion-postgres
def456         qdrant/qdrant:latest   ... Up (healthy)    fashion-qdrant
ghi789         fashion_agent-...      ... Up (healthy)    fashion-api
```

Nếu container chưa chạy:
```bash
cd /path/to/fashion_agent
docker compose up -d
# Đợi 30 giây cho containers khởi động
```

---

## Bước A.1: Kiểm tra dữ liệu trong PostgreSQL

```bash
# Đếm số items trong database
docker exec fashion-postgres psql -U fashion_user -d fashion_rag \
  -c "SELECT COUNT(*) AS total_items FROM fashion_items;"

# Đếm số items đã có caption + color (enrichment)
docker exec fashion-postgres psql -U fashion_user -d fashion_rag \
  -c "SELECT COUNT(*) AS enriched_items FROM fashion_item_enrichment WHERE caption IS NOT NULL AND color IS NOT NULL;"

# Xem vài dòng mẫu để biết format image_path hiện tại
docker exec fashion-postgres psql -U fashion_user -d fashion_rag \
  -c "SELECT image_id, label, image_path FROM fashion_items LIMIT 3;"
```

**📝 GHI LẠI** kết quả:
- Total items: ________
- Enriched items: ________
- Image path format: ________ (ví dụ: absolute hay relative?)

> Thông tin này sẽ dùng để verify sau khi import trên Windows.

---

## Bước A.2: Kiểm tra Qdrant

```bash
# Đếm vectors trong Qdrant
curl -s "http://localhost:6333/collections/fashion_products" | python3 -m json.tool
```

Tìm `points_count` trong output:
```json
{
  "result": {
    "status": "green",
    "points_count": 5127,    ← GHI LẠI SỐ NÀY
    ...
  }
}
```

**📝 GHI LẠI**: Qdrant points_count: ________

---

## Bước A.3: Tạo thư mục transfer

```bash
# Tạo folder chứa tất cả file export
mkdir -p ~/Desktop/fashion_transfer
```

---

## Bước A.4: Export PostgreSQL (pg_dump)

```bash
docker exec fashion-postgres pg_dump \
  -U fashion_user \
  -d fashion_rag \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  > ~/Desktop/fashion_transfer/fashion_rag_dump.sql
```

### Giải thích các flag:

| Flag | Tác dụng |
|------|----------|
| `-U fashion_user` | Kết nối bằng user này |
| `-d fashion_rag` | Dump database này |
| `--no-owner` | Không ghi `ALTER OWNER` (tránh lỗi permission trên Windows) |
| `--no-privileges` | Không ghi `GRANT/REVOKE` (cùng lý do) |
| `--clean` | Thêm `DROP TABLE IF EXISTS` trước `CREATE TABLE` (an toàn khi import lại) |
| `--if-exists` | Không lỗi nếu table chưa tồn tại |

### Verify:

```bash
# Kiểm tra file size
ls -lh ~/Desktop/fashion_transfer/fashion_rag_dump.sql
# Mong đợi: 5-20 MB

# Kiểm tra nội dung (xem có CREATE TABLE + INSERT/COPY)
head -30 ~/Desktop/fashion_transfer/fashion_rag_dump.sql

# Đếm số dòng data (xấp xỉ)
grep -c "COPY" ~/Desktop/fashion_transfer/fashion_rag_dump.sql
```

> [!WARNING]  
> Nếu file size = 0 hoặc rất nhỏ (<1 KB): có thể database name hoặc user sai.
> Chạy `docker exec fashion-postgres psql -U fashion_user -l` để xem danh sách databases.

---

## Bước A.5: Export Qdrant Snapshot

### Tạo snapshot:

```bash
curl -X POST "http://localhost:6333/collections/fashion_products/snapshots"
```

Output sẽ trả về JSON:
```json
{
  "result": {
    "name": "fashion_products-1234567890-2026-03-15.snapshot",
    "creation_time": "2026-03-15T12:00:00",
    "size": 234567890
  },
  "status": "ok"
}
```

**📝 GHI LẠI** snapshot name: ________________________________________

### Download snapshot:

```bash
# Thay <SNAPSHOT_NAME> bằng tên thực tế từ bước trên
SNAPSHOT_NAME="fashion_products-1234567890-2026-03-15.snapshot"   # ← THAY ĐỔI

curl -o ~/Desktop/fashion_transfer/fashion_products.snapshot \
  "http://localhost:6333/collections/fashion_products/snapshots/${SNAPSHOT_NAME}"
```

### Verify:

```bash
ls -lh ~/Desktop/fashion_transfer/fashion_products.snapshot
# Mong đợi: 50-500 MB
```

> [!WARNING]  
> Nếu file size < 1 MB: snapshot có thể bị lỗi.  
> Kiểm tra lại bằng: `curl -s "http://localhost:6333/collections/fashion_products/snapshots" | python3 -m json.tool`

---

## Bước A.6: Export ảnh từ container

Ảnh nằm ở đâu trong container phụ thuộc vào cách bạn ingest. Thử lần lượt:

```bash
# Phương án 1: Ảnh nằm trong kaggle cache
docker exec fashion-api ls /home/appuser/.cache/kagglehub/ 2>/dev/null && \
  echo "✅ Kaggle cache found"

# Phương án 2: Ảnh nằm ở dataset mount
docker exec fashion-api ls /app/dataset_images/ 2>/dev/null && \
  echo "✅ Dataset images found"

# Phương án 3: Ảnh nằm ở /app/images/
docker exec fashion-api ls /app/images/ 2>/dev/null && \
  echo "✅ App images found"
```

### Copy ảnh ra host:

```bash
# Nếu Phương án 1 (kaggle cache) — phổ biến nhất:
docker cp fashion-api:/home/appuser/.cache/kagglehub/datasets/agrigorev/clothing-dataset-full/versions/1/images_compressed/. \
  ~/Desktop/fashion_transfer/images/

# Nếu Phương án 2 (dataset_images):
docker cp fashion-api:/app/dataset_images/. ~/Desktop/fashion_transfer/images/

# Nếu Phương án 3 (app images):
docker cp fashion-api:/app/images/. ~/Desktop/fashion_transfer/images/
```

> [!IMPORTANT]
> Dấu `.` ở cuối path là quan trọng! Nó copy **nội dung** thư mục, không copy cả thư mục wrapper.

### Đếm ảnh:

```bash
ls ~/Desktop/fashion_transfer/images/ | wc -l
# Mong đợi: con số gần bằng total_items trong PostgreSQL
```

### Nén ảnh (tuỳ chọn — giảm thời gian copy USB):

```bash
cd ~/Desktop/fashion_transfer
tar czf images.tar.gz -C images .
ls -lh images.tar.gz
# Mong đợi: 500 MB - 3 GB
```

---

## Bước A.7: Kiểm tra toàn bộ transfer package

```bash
ls -lh ~/Desktop/fashion_transfer/
```

Kết quả mong đợi:
```
total ~1-5 GB
-rw-r--r--  fashion_rag_dump.sql         (~5-20 MB)
-rw-r--r--  fashion_products.snapshot    (~50-500 MB)
-rw-r--r--  images.tar.gz               (~500 MB - 3 GB)  ← hoặc thư mục images/
```

### Checklist trước khi copy sang USB:

```
□ fashion_rag_dump.sql     — kiểm tra: > 1 MB
□ fashion_products.snapshot — kiểm tra: > 10 MB
□ images/ hoặc images.tar.gz — kiểm tra: > 100 MB, có file .jpg
□ GHI LẠI: total_items = ____
□ GHI LẠI: enriched_items = ____
□ GHI LẠI: qdrant_points_count = ____
```

### Copy vào USB:

```bash
# Mount USB trên Mac (thường tự mount ở /Volumes/)
cp -r ~/Desktop/fashion_transfer/ /Volumes/USB_NAME/fashion_transfer/
```

---

# PHẦN B — Thực hiện trên Windows

> ⏱️ Thời gian: ~40 phút

## Bước B.0: Chuẩn bị

### Copy file từ USB vào Windows:

```powershell
# Tạo thư mục tạm
New-Item -ItemType Directory -Path "D:\fashion_transfer" -Force

# Copy từ USB (thay E: bằng ổ USB thực tế)
Copy-Item -Path "E:\fashion_transfer\*" -Destination "D:\fashion_transfer\" -Recurse
```

Verify:
```powershell
Get-ChildItem "D:\fashion_transfer" -Recurse | Select-Object Name, Length
```

---

## Bước B.1: Cài đặt / Fix Docker Desktop

### Trường hợp 1: Docker Desktop chưa cài

1. Tải từ https://www.docker.com/products/docker-desktop/
2. Cài đặt bình thường
3. Khi khởi động lần đầu, vào **Settings → Resources → Advanced**
4. Đổi **Disk image location** → `D:\DockerWSL`
5. Apply & Restart

### Trường hợp 2: Docker Desktop đã cài nhưng không chạy (tình trạng hiện tại của bạn)

Bạn có `docker_data.vhdx` ở `D:\DockerWSL\` nhưng Docker không nhận.

**Cách đơn giản nhất — Reset Docker Desktop:**

```powershell
# 1. Mở Docker Desktop
& "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 2. Vào Settings → Resources → Advanced
#    Đổi "Disk image location" → D:\DockerWSL
#    Nếu không thấy option này, tiếp tục bước 3

# 3. Nếu Docker báo lỗi, reset hoàn toàn:
#    Settings → Troubleshoot → Reset to factory defaults
#    Sau đó đổi lại Disk image location → D:\DockerWSL
```

> [!NOTE]  
> **Reset Docker KHÔNG mất dữ liệu của bạn** vì dữ liệu thực tế đang nằm trong
> SQL dump + Qdrant snapshot + images (đã export ở Phần A). Bạn sẽ import lại ở bước tiếp.

### Verify Docker đã chạy:

```powershell
docker version
docker ps
# Nếu thấy output bình thường → Docker OK ✅
```

---

## Bước B.2: Extract ảnh vào thư mục mount

```powershell
# Nếu transfer bằng tar.gz:
tar -xzf "D:\fashion_transfer\images.tar.gz" `
  -C "d:\awesome-llm-apps\llm-thesis\fashion_agent\images"

# Nếu transfer bằng thư mục images/:
Copy-Item -Path "D:\fashion_transfer\images\*" `
  -Destination "d:\awesome-llm-apps\llm-thesis\fashion_agent\images\" -Recurse
```

### Verify:

```powershell
(Get-ChildItem "d:\awesome-llm-apps\llm-thesis\fashion_agent\images\*.jpg" | Measure-Object).Count
# Mong đợi: gần bằng total_items đã ghi lại ở Phần A
```

---

## Bước B.3: Khởi động PostgreSQL + Qdrant

```powershell
docker compose -f "d:\awesome-llm-apps\llm-thesis\fashion_agent\docker-compose.yml" `
  up -d postgres qdrant
```

Đợi containers healthy (~15 giây):

```powershell
Start-Sleep -Seconds 15
docker ps
# Mong đợi:
# fashion-postgres   ... (healthy)
# fashion-qdrant     ... (healthy)
```

Nếu chưa healthy, đợi thêm:
```powershell
docker compose -f "d:\awesome-llm-apps\llm-thesis\fashion_agent\docker-compose.yml" `
  ps
```

---

## Bước B.4: Import PostgreSQL

### B.4a: Copy file SQL vào container:

```powershell
docker cp "D:\fashion_transfer\fashion_rag_dump.sql" fashion-postgres:/tmp/
```

### B.4b: Import:

```powershell
docker exec fashion-postgres psql `
  -U fashion_user -d fashion_rag `
  -f /tmp/fashion_rag_dump.sql
```

Bạn sẽ thấy output như:
```
SET
SET
DROP TABLE
CREATE TABLE
ALTER TABLE
COPY 5127
COPY 5127
...
```

### B.4c: Verify import:

```powershell
# Đếm total items
docker exec fashion-postgres psql -U fashion_user -d fashion_rag `
  -c "SELECT COUNT(*) AS total FROM fashion_items;"
# So sánh với con số ghi lại ở Phần A

# Đếm enriched items
docker exec fashion-postgres psql -U fashion_user -d fashion_rag `
  -c "SELECT COUNT(*) AS enriched FROM fashion_item_enrichment WHERE caption IS NOT NULL;"
# So sánh với con số ghi lại ở Phần A

# Xem image_path format hiện tại
docker exec fashion-postgres psql -U fashion_user -d fashion_rag `
  -c "SELECT image_path FROM fashion_items LIMIT 3;"
```

---

## Bước B.5: Fix image paths trong PostgreSQL

Image paths từ Mac có dạng absolute:
```
/home/appuser/.cache/kagglehub/datasets/.../images_compressed/abc123.jpg
```

Cần chuyển thành relative (chỉ filename):
```
abc123.jpg
```

```powershell
docker exec fashion-postgres psql -U fashion_user -d fashion_rag -c "
UPDATE fashion_items
SET image_path = regexp_replace(image_path, '.*/([^/]+)$', '\1'),
    updated_at = NOW()
WHERE image_path LIKE '%/%';
"
```

### Verify:

```powershell
docker exec fashion-postgres psql -U fashion_user -d fashion_rag `
  -c "SELECT image_path FROM fashion_items LIMIT 5;"
```

Kết quả mong đợi:
```
    image_path
------------------
 ea7b6656.jpg
 3f48c97d.jpg
 92ab1c5e.jpg
 ...
```

✅ Nếu thấy chỉ filename (không có `/`) → thành công!

---

## Bước B.6: Import Qdrant Snapshot

### B.6a: Copy snapshot vào container:

```powershell
docker exec fashion-qdrant mkdir -p /tmp/snapshots
docker cp "D:\fashion_transfer\fashion_products.snapshot" `
  fashion-qdrant:/tmp/snapshots/
```

### B.6b: Xoá collection cũ (nếu có) và recover từ snapshot:

```powershell
# Xoá collection cũ (nếu có)
docker exec fashion-qdrant curl -s -X DELETE `
  "http://localhost:6333/collections/fashion_products"

# Recover từ snapshot
docker exec fashion-qdrant curl -s -X PUT `
  "http://localhost:6333/collections/fashion_products/snapshots/recover" `
  -H "Content-Type: application/json" `
  -d '{"location": "/tmp/snapshots/fashion_products.snapshot"}'
```

### B.6c: Verify:

```powershell
# Kiểm tra collection
docker exec fashion-qdrant curl -s "http://localhost:6333/collections/fashion_products"
```

Tìm `points_count` — so sánh với số ghi lại ở Phần A.

---

## Bước B.7: Fix image paths trong Qdrant (QUAN TRỌNG!)

> [!WARNING]
> **Đây là bước mà nhiều người bỏ quên!** Qdrant cũng lưu `image_path` trong payload
> (xem `build_index.py` line 400). Search engine đọc `image_path` từ Qdrant payload,
> KHÔNG phải từ PostgreSQL. Nếu không fix ở đây, search vẫn trả về absolute Mac paths!

Tạo script Python tạm để update Qdrant payloads:

```powershell
# Chạy script bên trong container fashion-api (cần build trước)
# HOẶC chạy từ host bằng curl API

# Cách 1: Update bằng Qdrant REST API (scroll + set_payload)
# Tạo file script tạm
@"
import requests
import os

QDRANT_URL = "http://localhost:6333"
COLLECTION = "fashion_products"

# Scroll all points
offset = None
updated = 0
while True:
    params = {"limit": 100, "with_payload": True, "with_vector": False}
    if offset:
        params["offset"] = offset
    
    resp = requests.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll", json=params)
    data = resp.json()["result"]
    points = data["points"]
    
    for point in points:
        old_path = point["payload"].get("image_path", "")
        if "/" in old_path:
            new_path = old_path.rsplit("/", 1)[-1]  # extract filename
            # Update payload
            requests.post(
                f"{QDRANT_URL}/collections/{COLLECTION}/points/payload",
                json={
                    "payload": {"image_path": new_path},
                    "points": [point["id"]]
                }
            )
            updated += 1
    
    if data.get("next_page_offset") is None:
        break
    offset = data["next_page_offset"]

print(f"Updated {updated} Qdrant payloads")
"@ | Set-Content -Path "D:\fashion_transfer\fix_qdrant_paths.py"

# Chạy script (cần Python + requests)
python "D:\fashion_transfer\fix_qdrant_paths.py"
```

> [!NOTE]
> Nếu bạn chưa cài Python trên Windows hoặc chưa có `requests`:
> ```powershell
> pip install requests
> python "D:\fashion_transfer\fix_qdrant_paths.py"
> ```
> Hoặc chạy script bên trong Docker container (xem "Cách thay thế" phía dưới).

### Cách thay thế — Chạy trong Docker container:

```powershell
# Copy script vào container
docker cp "D:\fashion_transfer\fix_qdrant_paths.py" fashion-qdrant:/tmp/

# Cài requests trong qdrant container (container dùng Python)
docker exec fashion-qdrant pip install requests 2>$null

# Chạy script — nhưng cần đổi QDRANT_URL thành localhost vì chạy trong container
docker exec fashion-qdrant python /tmp/fix_qdrant_paths.py
```

### Verify:

```powershell
# Scroll 3 points và check image_path
docker exec fashion-qdrant curl -s -X POST `
  "http://localhost:6333/collections/fashion_products/points/scroll" `
  -H "Content-Type: application/json" `
  -d '{"limit": 3, "with_payload": true, "with_vector": false}'
```

Kiểm tra `image_path` — phải là filename only (không có `/`).

---

## Bước B.8: Build và khởi động full stack

```powershell
# Build fashion-api image
docker compose -f "d:\awesome-llm-apps\llm-thesis\fashion_agent\docker-compose.yml" `
  build fashion-api

# Khởi động toàn bộ stack
docker compose -f "d:\awesome-llm-apps\llm-thesis\fashion_agent\docker-compose.yml" `
  up -d
```

Đợi tất cả services healthy:

```powershell
Start-Sleep -Seconds 30
docker ps
```

Kết quả mong đợi:
```
CONTAINER ID   IMAGE                        STATUS          NAMES
...            postgres:16-alpine           Up (healthy)    fashion-postgres
...            qdrant/qdrant:latest         Up (healthy)    fashion-qdrant
...            fashion_agent-fashion-api    Up (healthy)    fashion-api
...            cloudflare/cloudflared       Up              fashion-cloudflared
```

---

## Bước B.9: Test ứng dụng

### Test health endpoint:

```powershell
# PowerShell
(Invoke-WebRequest -Uri "http://localhost:8000/health").Content
```

Mong đợi:
```json
{"status":"healthy","version":"1.0.0","services":{"postgresql":"healthy","qdrant":"healthy"}}
```

### Mở Gradio UI:

```powershell
Start-Process "http://localhost:8000"
```

### Test tìm kiếm thử:

Gõ trong chat: **"tìm áo sơ mi trắng"**

✅ Nếu thấy kết quả + ảnh hiển thị → **THÀNH CÔNG!** 🎉

---

# ✅ Checklist hoàn thành

```
PHẦN A — MacBook
  □ A.0  Docker containers đang chạy
  □ A.1  Ghi lại total_items = ____ & enriched_items = ____
  □ A.2  Ghi lại qdrant_points_count = ____
  □ A.3  Tạo thư mục fashion_transfer
  □ A.4  Export pg_dump (check file > 1 MB)
  □ A.5  Export Qdrant snapshot (check file > 10 MB)
  □ A.6  Export images (check: số file ≈ total_items)
  □ A.7  Copy tất cả vào USB

PHẦN B — Windows
  □ B.0  Copy từ USB vào D:\fashion_transfer
  □ B.1  Docker Desktop chạy OK (docker ps works)
  □ B.2  Extract images → fashion_agent/images/ (check: số file đúng)
  □ B.3  docker compose up -d postgres qdrant (healthy)
  □ B.4  Import SQL dump (count phải bằng Phần A)
  □ B.5  Fix PG image paths → relative filenames
  □ B.6  Import Qdrant snapshot (points_count phải bằng Phần A)
  □ B.7  Fix Qdrant image paths → relative filenames
  □ B.8  Build + start full stack (4 containers healthy)
  □ B.9  Test: http://localhost:8000 → search + ảnh hiển thị OK
```

---

# 🔧 Troubleshooting

## Lỗi: `pg_dump` tạo file rỗng

```bash
# Kiểm tra database list
docker exec fashion-postgres psql -U fashion_user -l
# Kiểm tra user
docker exec fashion-postgres psql -U fashion_user -d fashion_rag -c "SELECT current_user;"
```

## Lỗi: Qdrant snapshot recover failed

```powershell
# Tạo collection trước rồi recover
docker exec fashion-qdrant curl -s -X PUT `
  "http://localhost:6333/collections/fashion_products" `
  -H "Content-Type: application/json" `
  -d '{"vectors":{"image":{"size":768,"distance":"Cosine"},"text":{"size":768,"distance":"Cosine"}}}'

# Rồi recover lại
docker exec fashion-qdrant curl -s -X PUT `
  "http://localhost:6333/collections/fashion_products/snapshots/recover" `
  -H "Content-Type: application/json" `
  -d '{"location":"/tmp/snapshots/fashion_products.snapshot"}'
```

## Lỗi: Ảnh không hiển thị trong Gradio

1. Kiểm tra ảnh có trong mount path:
```powershell
docker exec fashion-api ls /app/dataset_images/ | head -5
```

2. Nếu trống → kiểm tra .env:
```powershell
Get-Content "d:\awesome-llm-apps\llm-thesis\fashion_agent\.env" | Select-String "DATASET_IMAGES"
# Phải là: DATASET_IMAGES_HOST_PATH=d:\awesome-llm-apps\llm-thesis\fashion_agent\images
```

3. Kiểm tra docker-compose mount:
```yaml
# docker-compose.yml line 78
- ${DATASET_IMAGES_HOST_PATH:-./images}:/app/dataset_images:ro
```

## Lỗi: Search trả về kết quả nhưng không có ảnh

→ Có thể chưa fix image paths trong Qdrant (Bước B.7). Kiểm tra:
```powershell
docker exec fashion-qdrant curl -s -X POST `
  "http://localhost:6333/collections/fashion_products/points/scroll" `
  -H "Content-Type: application/json" `
  -d '{"limit":1,"with_payload":true,"with_vector":false}'
```
Nếu `image_path` còn chứa `/` → chạy lại Bước B.7.

## Lỗi: Docker container fashion-api crash loop

```powershell
# Xem logs
docker logs fashion-api --tail 50

# Thường gặp:
# - GEMINI_API_KEY không hợp lệ → kiểm tra .env
# - PostgreSQL connection refused → đợi postgres healthy
# - Module not found → build lại: docker compose build fashion-api
```

## Lỗi: PowerShell curl không hoạt động

Windows PowerShell alias `curl` = `Invoke-WebRequest`. Thay bằng:
```powershell
# Dùng docker exec thay vì gọi curl trực tiếp
docker exec fashion-qdrant curl -s "http://localhost:6333/..."
```

---

# 📊 So sánh: Transfer vs Re-run

| Hạng mục | Transfer (guide này) | Re-run từ đầu |
|----------|---------------------|----------------|
| **Gemini captions** (~15K × 1.5s) | ✅ Giữ nguyên | ❌ ~6 giờ + tokens |
| **Gemini colors** (~15K × 1.5s) | ✅ Giữ nguyên | ❌ ~6 giờ + tokens |
| **FashionSigLIP encoding** | ✅ Giữ nguyên | ❌ ~2-4 giờ (CPU) |
| **Kaggle download** (6.5 GB) | ✅ Đã có ảnh | ❌ ~30 phút |
| **Tổng thời gian** | **~1 giờ** | **~14-16 giờ** |
| **Chi phí API** | **$0** | **Nhiều Gemini tokens** |

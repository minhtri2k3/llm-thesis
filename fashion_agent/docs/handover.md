# Hướng dẫn bàn giao và chạy hệ thống trên Windows

> Tài liệu này dành cho bên nhận bàn giao để chạy được toàn bộ hệ thống trên máy Windows bằng Docker Desktop.
> Nội dung dưới đây bám theo source hiện tại trong repo, đặc biệt là `start.sh` và `fashion_agent/docker-compose.yml`.

---

## 1. Kết luận ngắn trước khi bàn giao

- Có thể chạy trên **Windows**.
- **Không nên dùng `start.sh` trên Windows**. File này là wrapper Bash để tiện chạy trên macOS/Linux.
- Cách ổn định nhất để bàn giao là: **source code + file `.env` + 2 file backup Docker volumes + thư mục ảnh dataset**.
- Nếu chỉ đưa **Docker image đã build sẵn** thì **chưa đủ** để hệ thống chạy hoàn chỉnh, vì dự án còn phụ thuộc vào:
  - dữ liệu PostgreSQL,
  - dữ liệu Qdrant,
  - file `.env`,
  - thư mục ảnh dataset,
  - và có thể cả cache model nếu muốn chạy ngay không cần tải thêm.
- Nếu image được build trên **Mac Apple Silicon**, rất có thể nó là **`linux/arm64`** và **không phù hợp để đưa thẳng sang máy Windows phổ biến (`amd64`)**.

**Khuyến nghị bàn giao:** để bên trường chạy `docker compose` trực tiếp từ source trên Windows, thay vì gửi “1 Docker image” đã build trên máy Mac.

---

## 2. `start.sh` hiện đang làm gì

File gốc: `/Users/tringuyen/llm-thesis/start.sh`

`start.sh` chỉ là script tiện ích, không phải thành phần bắt buộc của hệ thống. Nó làm 4 việc chính:

1. Chuyển vào thư mục `fashion_agent/`.
2. Gọi `docker compose` với file `fashion_agent/docker-compose.yml`.
3. Khởi động trước `postgres` và `qdrant`, đợi healthcheck xanh.
4. Khởi động toàn bộ stack, rồi đọc log của `cloudflared-fe` để lấy URL `trycloudflare.com`.

### Vì sao không nên dùng `start.sh` trên Windows

- Script viết bằng **Bash**, không phải PowerShell.
- Có đoạn thêm PATH riêng cho **Docker Desktop trên macOS**.
- Dùng các lệnh shell kiểu Unix như `grep`, `tail`, `seq`.
- Mục tiêu của nó là tiện thao tác local, không phải script bàn giao đa nền tảng.

**Kết luận:** trên Windows, bỏ qua `start.sh` và chạy thẳng bằng `docker compose` trong thư mục `fashion_agent`.

---

## 3. Bên nhận cần được bàn giao những gì

Bàn giao tối thiểu các mục sau:

1. **Source code của repo** `llm-thesis`
2. **File `fashion_agent/.env`**
3. **File `fashion_agent/pgdata_backup.tar.gz`**
4. **File `fashion_agent/qdrant_backup.tar.gz`**
5. **Thư mục ảnh dataset** dùng cho hiển thị ảnh sản phẩm

Bàn giao thêm nếu muốn giảm thời gian khởi động lần đầu:

6. **Thư mục `fashion_agent/models/`**

### Ý nghĩa từng phần

- `source code`: chứa Dockerfile, compose file, backend, frontend.
- `.env`: chứa cấu hình môi trường và API key.
- `pgdata_backup.tar.gz`: chứa dữ liệu PostgreSQL đã xử lý.
- `qdrant_backup.tar.gz`: chứa vector database đã index sẵn.
- `dataset images`: ảnh sản phẩm để frontend/API hiển thị đúng.
- `models/`: cache model HuggingFace; nếu không bàn giao thư mục này thì máy mới vẫn chạy được, nhưng lần đầu sẽ phải tải model từ Internet.

---

## 4. Yêu cầu máy bên nhận

### Phần mềm bắt buộc

- **Windows 10/11**
- **Docker Desktop**
- Docker Desktop nên chạy ở chế độ **Linux containers**
- Khuyến nghị bật **WSL2 backend** trong Docker Desktop

### Tài nguyên khuyến nghị

- **RAM tối thiểu:** 8 GB
- **RAM khuyến nghị:** 16 GB
- **Dung lượng trống:** ít nhất 10 GB
- **Internet:** cần nếu chưa có sẵn thư mục `models/`

### Port cần trống

- `3000` — frontend web
- `8000` — backend API
- `5432` — PostgreSQL
- `6333` — Qdrant

---

## 5. Cấu trúc chạy thực tế của dự án

Compose file hiện tại ở: `fashion_agent/docker-compose.yml`

Stack hiện tại gồm các service sau:

- `postgres`
- `qdrant`
- `fashion-api`
- `clothie-web`
- `cloudflared-fe`
- `ngrok-fe` (chỉ chạy khi bật profile `ngrok`)

### URL khi chạy local

- Frontend chính: `http://localhost:3000`
- Backend API: `http://localhost:8000`

Lưu ý:

- Frontend `clothie-web` chạy ở cổng `3000` và reverse proxy API sang `fashion-api`.
- Nếu chỉ kiểm tra backend thì có thể vào trực tiếp `http://localhost:8000`.

---

## 6. File `.env` cần đặt ở đâu

Bên nhận phải đặt file tại đúng đường dẫn:

`fashion_agent/.env`

Không nên phụ thuộc vào file mẫu cũ trong docs. Source hiện tại **không có** `.env.example` ở ngay thư mục `fashion_agent/`; file mẫu đang nằm trong docs và chỉ nên xem như tài liệu tham khảo.

### Các biến quan trọng phải có trong `.env`

- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`
- `PG_PASSWORD`
- `GEMINI_API_KEY`
- `DATASET_IMAGES_HOST_PATH`

### Ghi chú quan trọng

- `PGPASSWORD` và `PG_PASSWORD` nên để **cùng một giá trị**.
- `DATASET_IMAGES_HOST_PATH` trên Windows nên dùng dạng:
  - `C:/data/fashion/images`
  - không nên dùng đường dẫn có dấu `\` nếu tránh được.

---

## 7. Phương án bàn giao khuyến nghị

### Nên dùng phương án này

Bên trường nhận:

- repo source,
- file `.env`,
- 2 file backup volume,
- thư mục ảnh dataset,
- tùy chọn: thư mục `models/`.

Sau đó họ tự chạy `docker compose` trên Windows.

### Vì sao đây là phương án tốt nhất

- Không bị lệ thuộc kiến trúc CPU của máy build cũ.
- Không cần chuyển Docker image giữa Mac và Windows.
- Dữ liệu PostgreSQL và Qdrant được phục hồi đúng từ backup.
- Dễ sửa cấu hình môi trường sau bàn giao.

---

## 8. Phương án “chỉ bàn giao 1 Docker image” có được không

### Trả lời ngắn

**Có thể, nhưng không khuyến nghị và không đủ cho trường hợp này.**

### Lý do

Nếu chỉ đưa image đã build sẵn thì vẫn còn thiếu:

- dữ liệu PostgreSQL,
- dữ liệu Qdrant,
- file `.env`,
- dataset images,
- cache model nếu muốn chạy ngay.

Ngoài ra còn một rủi ro rất lớn:

- Image build trên **Mac Apple Silicon** thường là `linux/arm64`.
- Máy Windows bên nhận thường là `linux/amd64` qua Docker Desktop.
- Vì vậy image export từ Mac có thể **không chạy được** trên Windows nếu không build đúng kiến trúc.

### Khi nào mới nên bàn giao image

Chỉ nên làm nếu:

- build image theo **`linux/amd64`** hoặc multi-arch,
- và vẫn bàn giao kèm dữ liệu volume cùng file `.env`.

**Kết luận:** với dự án này, bàn giao **source + compose + backup data** là an toàn nhất.

---

## 9. Các bước chạy trên Windows

Phần này giả sử bên nhận dùng **PowerShell** và đã mở Docker Desktop.

### Bước 1. Nhận và giải nén source

Giải nén hoặc clone repo vào một thư mục, ví dụ:

`C:/projects/llm-thesis`

Sau đó mở PowerShell và đi vào:

```powershell
cd C:/projects/llm-thesis/fashion_agent
```

### Bước 2. Đặt file `.env`

Đảm bảo file này tồn tại:

`C:/projects/llm-thesis/fashion_agent/.env`

Nếu bên nhận được gửi sẵn `.env` thì chỉ cần copy đúng vị trí.

### Bước 3. Chuẩn bị thư mục ảnh dataset

Ví dụ đặt tại:

`C:/projects/fashion-dataset/images`

Sau đó sửa `DATASET_IMAGES_HOST_PATH` trong `.env` thành:

```ini
DATASET_IMAGES_HOST_PATH=C:/projects/fashion-dataset/images
```

Nếu không có thư mục ảnh, hệ thống vẫn có thể chạy nhưng phần hiển thị ảnh sản phẩm sẽ không đầy đủ hoặc không đúng.

### Bước 4. Đặt 2 file backup vào thư mục `fashion_agent`

Cần có:

- `pgdata_backup.tar.gz`
- `qdrant_backup.tar.gz`

trong thư mục:

`C:/projects/llm-thesis/fashion_agent`

### Bước 5. Import Docker volumes

Chạy lần lượt:

```powershell
docker volume create fashion_agent_pgdata
docker run --rm -v fashion_agent_pgdata:/data -v "${PWD}:/backup" alpine tar xzf /backup/pgdata_backup.tar.gz -C /data
```

```powershell
docker volume create fashion_agent_qdrant_data
docker run --rm -v fashion_agent_qdrant_data:/data -v "${PWD}:/backup" alpine tar xzf /backup/qdrant_backup.tar.gz -C /data
```

Kiểm tra lại:

```powershell
docker volume ls --filter name=fashion_agent
```

Kết quả mong đợi có:

- `fashion_agent_pgdata`
- `fashion_agent_qdrant_data`

### Bước 6. Khởi động hệ thống

Khởi động đầy đủ toàn bộ stack:

```powershell
docker compose up -d
```

Lệnh này sẽ chạy:

- `postgres`
- `qdrant`
- `fashion-api`
- `clothie-web`
- `cloudflared-fe`

### Bước 7. Kiểm tra trạng thái container

```powershell
docker compose ps
```

Mong đợi:

- `fashion-postgres` ở trạng thái `healthy`
- `fashion-qdrant` ở trạng thái `healthy`
- `fashion-api` đang `Up`
- `fashion-clothie-web` đang `Up`

### Bước 8. Theo dõi log backend khi khởi động lần đầu

```powershell
docker compose logs -f fashion-api
```

Nếu chưa bàn giao sẵn thư mục `models/`, lần đầu có thể mất vài phút để tải model.

### Bước 9. Truy cập hệ thống

- Frontend chính: `http://localhost:3000`
- Backend API: `http://localhost:8000`

Nếu muốn kiểm tra health API:

```powershell
curl http://localhost:8000/health
```

---

## 10. Public URL: cần hiểu đúng theo source hiện tại

Source hiện tại có 2 cách public access:

### Cách 1. Quick Tunnel qua `cloudflared-fe`

Đây là cách mặc định khi chạy `docker compose up -d`.

Đặc điểm:

- không cần cấu hình token trong compose hiện tại,
- URL là dạng `https://...trycloudflare.com`,
- URL có thể thay đổi giữa các lần chạy.

Xem URL bằng log:

```powershell
docker compose logs cloudflared-fe
```

### Cách 2. Ngrok profile

Compose hiện tại có service `ngrok-fe`, nhưng chỉ chạy khi bật profile `ngrok`.

Nếu bên nhận có `NGROK_AUTHTOKEN` và domain phù hợp trong `.env`, có thể chạy:

```powershell
docker compose --profile ngrok up -d
```

### Lưu ý quan trọng

Các tài liệu cũ có nhắc `CF_TUNNEL_TOKEN`, nhưng **compose hiện tại không dùng token đó** cho `cloudflared-fe`.
Vì vậy khi bàn giao, đừng dựa vào hướng dẫn cũ nói rằng phải có `CF_TUNNEL_TOKEN` để chạy được tunnel mặc định.

---

## 11. Nếu chỉ muốn chạy local, không cần tunnel

Có thể chỉ bật các service cần thiết:

```powershell
docker compose up -d postgres qdrant fashion-api clothie-web
```

Cách này bỏ qua public tunnel và vẫn dùng đầy đủ hệ thống local tại:

- `http://localhost:3000`
- `http://localhost:8000`

---

## 12. Nếu chưa có backup data thì sao

Nếu không có `pgdata_backup.tar.gz` và `qdrant_backup.tar.gz`, vẫn có thể chạy từ đầu, nhưng sẽ lâu hơn rất nhiều vì phải:

1. ingest dữ liệu vào PostgreSQL,
2. tạo caption/enrichment,
3. build embedding và index vào Qdrant.

Đây **không phải** phương án phù hợp cho bàn giao nhanh cho bên trường.

Với mục tiêu bàn giao, nên dùng backup volumes đã có sẵn.

---

## 13. Các lệnh vận hành an toàn

### Xem trạng thái

```powershell
docker compose ps
```

### Xem log backend

```powershell
docker compose logs -f fashion-api
```

### Xem log frontend

```powershell
docker compose logs -f clothie-web
```

### Dừng hệ thống nhưng giữ data

```powershell
docker compose stop
```

hoặc

```powershell
docker compose down
```

### Bật lại sau khi đã dừng

```powershell
docker compose up -d
```

---

## 14. Các lệnh không được dùng khi bàn giao

**Tuyệt đối tránh:**

```powershell
docker compose down -v
```

Lệnh này sẽ xóa volumes, đồng nghĩa với mất:

- dữ liệu PostgreSQL,
- dữ liệu Qdrant.

Cũng không nên chạy:

```powershell
docker volume rm fashion_agent_pgdata
docker volume rm fashion_agent_qdrant_data
```

trừ khi chủ động muốn xóa sạch dữ liệu để làm lại từ đầu.

---

## 15. Sự cố thường gặp

### 1. `PG_PASSWORD is required`

Nguyên nhân: file `.env` thiếu biến `PG_PASSWORD`.

Cách xử lý: kiểm tra lại `fashion_agent/.env`.

### 2. `GEMINI_API_KEY is required`

Nguyên nhân: thiếu API key trong `.env`.

Cách xử lý: điền lại `GEMINI_API_KEY`.

### 3. PostgreSQL báo sai mật khẩu

Nguyên nhân: `PG_PASSWORD` trong `.env` không khớp với dữ liệu đã backup.

Cách xử lý: dùng đúng file `.env` được bàn giao cùng backup.

### 4. Không hiển thị ảnh sản phẩm

Nguyên nhân thường gặp:

- `DATASET_IMAGES_HOST_PATH` sai,
- thư mục ảnh chưa được copy sang máy Windows,
- đường dẫn dùng sai format Windows.

Cách xử lý:

- kiểm tra thư mục có tồn tại thật không,
- dùng đường dẫn kiểu `C:/.../...` trong `.env`.

### 5. `fashion-api` khởi động rất lâu

Nguyên nhân thường gặp:

- máy đang tải model lần đầu,
- chưa có thư mục `models/` được bàn giao.

Cách xử lý:

- chờ thêm,
- hoặc bàn giao sẵn thư mục `fashion_agent/models/`.

### 6. Port bị chiếm

Kiểm tra dịch vụ khác đang dùng các port `3000`, `8000`, `5432`, `6333`.

Nếu cần, có thể sửa phần `ports` trong `fashion_agent/docker-compose.yml`.

---

## 16. Checklist bàn giao thực tế

Trước khi gửi cho bên trường, nên kiểm tra đủ các mục sau:

- [ ] Repo source đầy đủ
- [ ] File `fashion_agent/.env`
- [ ] File `fashion_agent/pgdata_backup.tar.gz`
- [ ] File `fashion_agent/qdrant_backup.tar.gz`
- [ ] Thư mục ảnh dataset
- [ ] Ghi rõ URL local dùng để test: `3000` và `8000`
- [ ] Ghi rõ không dùng `start.sh` trên Windows
- [ ] Ghi rõ không chạy `docker compose down -v`
- [ ] Tùy chọn: bàn giao thêm thư mục `fashion_agent/models/`

---

## 17. Khuyến nghị cuối cùng

Nếu mục tiêu là để bên trường chạy ổn định trên Windows, phương án tốt nhất là:

1. gửi source code,
2. gửi `.env`,
3. gửi 2 file backup volumes,
4. gửi dataset images,
5. để họ chạy bằng `docker compose` trong thư mục `fashion_agent`.

**Không nên coi `start.sh` là entrypoint bàn giao.**
Nó chỉ là script tiện cho máy local hiện tại.

**Không nên chỉ gửi 1 Docker image build từ Mac** rồi kỳ vọng Windows chạy ngay.
Rủi ro kiến trúc `arm64` và thiếu data phụ trợ là rất cao.

---

*Tài liệu này đã được cập nhật theo source hiện tại của repo, bao gồm `start.sh`, `fashion_agent/docker-compose.yml`, `fashion_agent/Dockerfile`, và `clothie_web/Dockerfile`.*

# Hướng dẫn cho giáo viên chạy dự án trên Windows

> Tài liệu này hướng dẫn chạy dự án sau khi nhận **nguyên thư mục dự án đầy đủ** qua Google Drive.
> Cách chạy được khuyến nghị là dùng Docker Desktop trên Windows.

---

## 1. Trả lời ngắn gọn

**Có.** Nếu người bàn giao đã upload **nguyên thư mục đầy đủ thật**, trong đó có:

- source code,
- file `fashion_agent/.env`,
- file `fashion_agent/pgdata_backup.tar.gz`,
- file `fashion_agent/qdrant_backup.tar.gz`,
- thư mục ảnh `fashion_agent/images/` hoặc một thư mục ảnh tương đương,
- và tốt nhất là cả `fashion_agent/models/`,

thì bên nhận trên Windows **đủ điều kiện để chạy Docker**.

Tuy nhiên, có 1 bước bắt buộc trước khi chạy là:

- **import 2 file backup `.tar.gz` vào Docker volumes**.

Nói ngắn gọn:

- **có đủ file** → **đủ để run**,
- nhưng vẫn phải làm đúng quy trình import data rồi mới `docker compose up -d`.

---

## 2. Yêu cầu máy chạy

### Hệ điều hành

- Windows 10 hoặc Windows 11

### Phần mềm cần cài

- Docker Desktop

### Cấu hình khuyến nghị

- RAM tối thiểu: 8 GB
- RAM khuyến nghị: 16 GB
- Dung lượng trống: từ 10 GB trở lên
- Có Internet nếu chưa có sẵn thư mục `models/`

---

## 3. Sau khi tải từ Google Drive về

Giả sử thư mục dự án được giải nén tại:

`C:/projects/llm-thesis`

Thư mục cần chạy là:

`C:/projects/llm-thesis/fashion_agent`

Mở **PowerShell** và chuyển vào thư mục đó:

```powershell
cd C:/projects/llm-thesis/fashion_agent
```

---

## 4. Kiểm tra các file cần có

Trong thư mục `fashion_agent`, cần có các thành phần sau:

- `.env`
- `docker-compose.yml`
- `Dockerfile`
- `pgdata_backup.tar.gz`
- `qdrant_backup.tar.gz`
- thư mục `images/`
- tùy chọn: thư mục `models/`

### Nếu đã có đủ các file trên

Thì có thể chạy dự án bằng Docker sau khi import volumes.

### Nếu thiếu `pgdata_backup.tar.gz` hoặc `qdrant_backup.tar.gz`

Hệ thống vẫn có thể dựng lại về mặt kỹ thuật, nhưng sẽ không còn dữ liệu đã chuẩn bị sẵn, và việc dựng lại sẽ tốn rất nhiều thời gian.

### Nếu thiếu `models/`

Hệ thống vẫn có thể chạy, nhưng lần đầu sẽ tải model AI từ Internet và chờ lâu hơn.

---

## 5. Ý nghĩa các thành phần

### `.env`

Chứa cấu hình môi trường, ví dụ:

- mật khẩu PostgreSQL,
- Gemini API key,
- đường dẫn thư mục ảnh dataset.

### `pgdata_backup.tar.gz`

Chứa dữ liệu PostgreSQL đã được chuẩn bị sẵn.

### `qdrant_backup.tar.gz`

Chứa vector database đã index sẵn để tìm kiếm.

### `images/`

Chứa ảnh sản phẩm để hệ thống hiển thị ảnh.

### `models/`

Chứa cache model AI. Nếu thư mục này đã có sẵn thì thời gian chạy lần đầu sẽ nhanh hơn rất nhiều.

---

## 6. Cấu hình file `.env`

File `.env` phải nằm đúng tại:

`fashion_agent/.env`

Trong file này, biến quan trọng nhất cần đúng là:

- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`
- `PG_PASSWORD`
- `GEMINI_API_KEY`
- `DATASET_IMAGES_HOST_PATH`

### Lưu ý cho Windows

Nếu đang dùng thư mục ảnh nằm ngay trong folder bàn giao, nên để:

```ini
DATASET_IMAGES_HOST_PATH=C:/projects/llm-thesis/fashion_agent/images
```

Nếu ảnh nằm chỗ khác, đổi thành đường dẫn thực tế tương ứng.

Không nên dùng đường dẫn kiểu Linux hoặc macOS trong máy Windows.

---

## 7. Bước bắt buộc: import dữ liệu Docker volumes

Dự án này dùng **Docker named volumes** cho PostgreSQL và Qdrant.
Vì vậy, dù đã tải đủ thư mục từ Google Drive, vẫn cần import dữ liệu từ 2 file backup.

### Bước 7.1: Tạo volume PostgreSQL và import dữ liệu

```powershell
docker volume create fashion_agent_pgdata
docker run --rm -v fashion_agent_pgdata:/data -v "${PWD}:/backup" alpine tar xzf /backup/pgdata_backup.tar.gz -C /data
```

### Bước 7.2: Tạo volume Qdrant và import dữ liệu

```powershell
docker volume create fashion_agent_qdrant_data
docker run --rm -v fashion_agent_qdrant_data:/data -v "${PWD}:/backup" alpine tar xzf /backup/qdrant_backup.tar.gz -C /data
```

### Bước 7.3: Kiểm tra volume đã tạo

```powershell
docker volume ls --filter name=fashion_agent
```

Kỳ vọng nhìn thấy:

- `fashion_agent_pgdata`
- `fashion_agent_qdrant_data`

---

## 8. Khởi động hệ thống

Sau khi import xong dữ liệu, chạy:

```powershell
docker compose up -d
```

Lệnh này sẽ khởi động các dịch vụ chính của dự án.

### Các service chính

- `postgres`
- `qdrant`
- `fashion-api`
- `clothie-web`
- `cloudflared-fe`

---

## 9. Kiểm tra trạng thái sau khi chạy

```powershell
docker compose ps
```

Kỳ vọng:

- PostgreSQL ở trạng thái healthy
- Qdrant ở trạng thái healthy
- API đang chạy
- Frontend đang chạy

Nếu muốn xem log backend:

```powershell
docker compose logs -f fashion-api
```

Nếu muốn xem log frontend:

```powershell
docker compose logs -f clothie-web
```

---

## 10. Truy cập hệ thống

Sau khi các container đã chạy:

- Giao diện web chính: `http://localhost:3000`
- API backend: `http://localhost:8000`

Nếu muốn kiểm tra backend nhanh:

```powershell
curl http://localhost:8000/health
```

---

## 11. Nếu lần đầu chạy rất chậm

Điều này là bình thường nếu thư mục `models/` chưa có sẵn.
Khi đó hệ thống sẽ tải model AI từ Internet trong lần chạy đầu tiên.

Khuyến nghị:

- nếu bàn giao được, nên gửi kèm luôn thư mục `fashion_agent/models/`.

---

## 12. Nếu chỉ muốn chạy local, không cần public URL

Vẫn có thể dùng lệnh:

```powershell
docker compose up -d
```

và chỉ cần truy cập bằng:

- `http://localhost:3000`
- `http://localhost:8000`

Không cần làm thêm bước nào khác.

---

## 13. Những lỗi thường gặp

### Thiếu `GEMINI_API_KEY`

Dấu hiệu: backend không khởi động được.

Cách xử lý: kiểm tra lại file `.env`.

### Sai `PG_PASSWORD`

Dấu hiệu: PostgreSQL không đăng nhập được hoặc API không kết nối được DB.

Cách xử lý: dùng đúng file `.env` được bàn giao cùng backup.

### Không có dữ liệu tìm kiếm

Dấu hiệu: hệ thống chạy nhưng không ra kết quả đúng.

Nguyên nhân thường gặp:

- chưa import 2 file backup volume,
- hoặc backup không đúng.

### Không hiển thị ảnh

Nguyên nhân thường gặp:

- `DATASET_IMAGES_HOST_PATH` sai,
- thư mục ảnh không tồn tại,
- đường dẫn trong `.env` không đúng chuẩn Windows.

### Cổng bị trùng

Nếu máy đã dùng sẵn các cổng `3000`, `8000`, `5432`, hoặc `6333`, Docker có thể không khởi động được.

---

## 14. Cách tắt và bật lại hệ thống

### Dừng nhưng giữ dữ liệu

```powershell
docker compose stop
```

hoặc

```powershell
docker compose down
```

### Bật lại

```powershell
docker compose up -d
```

---

## 15. Cảnh báo quan trọng

**Không dùng lệnh sau nếu muốn giữ dữ liệu:**

```powershell
docker compose down -v
```

Lệnh này sẽ xóa toàn bộ Docker volumes của PostgreSQL và Qdrant.
Khi đó hệ thống sẽ mất dữ liệu đã dựng sẵn.

Cũng không nên xóa các volume sau nếu chưa có chủ đích:

```powershell
docker volume rm fashion_agent_pgdata
docker volume rm fashion_agent_qdrant_data
```

---

## 16. Kết luận

Nếu người bàn giao đã upload **nguyên thư mục đầy đủ thật** lên Google Drive, bao gồm:

- source code,
- `.env`,
- `pgdata_backup.tar.gz`,
- `qdrant_backup.tar.gz`,
- thư mục ảnh,
- và tốt nhất là cả `models/`,

thì bên nhận trên Windows **đủ để chạy Docker**.

Điều cần nhớ là:

1. tải folder về,
2. vào thư mục `fashion_agent`,
3. import 2 file backup vào Docker volumes,
4. chạy `docker compose up -d`,
5. mở `http://localhost:3000` để dùng hệ thống.

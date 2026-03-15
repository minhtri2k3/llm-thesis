## 1. Fix serve_image endpoint

- [x] 1.1 Trong `api/main.py` hàm `serve_image()`, đổi `IMAGES_DIR` → `DATASET_IMAGES_DIR` với fallback tìm tiếp ở `IMAGES_DIR`

## 2. Rebuild & Test

- [x] 2.1 Rebuild Docker image (`docker compose build fashion-api`) và restart
- [x] 2.2 Test truy cập ảnh qua browser: `http://localhost:8000/api/images/{uuid}.jpg` — xác nhận trả về 200
- [x] 2.3 Test trên Gradio UI: gửi query, xác nhận ảnh hiển thị inline thành công

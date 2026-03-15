# Fix Image 404 — Sửa endpoint serve ảnh sản phẩm

## Why

Endpoint `GET /api/images/{filename}` trả về **404 Not Found** cho tất cả ảnh sản phẩm. Nguyên nhân: endpoint tìm ảnh trong `IMAGES_DIR` (thư mục `images/`, trống) thay vì `DATASET_IMAGES_DIR` (`/app/dataset_images/`, mount từ Kaggle dataset).

## What Changes

- Sửa hàm `serve_image()` trong `api/main.py`: đổi `IMAGES_DIR` → `DATASET_IMAGES_DIR`
- Thêm fallback: tìm ở `IMAGES_DIR` trước, nếu không có thì tìm ở `DATASET_IMAGES_DIR`

## Impact

- **File bị ảnh hưởng:** `api/main.py` (chỉ 1 file, sửa ~3 dòng)
- **KHÔNG đụng:** `pre_processing/`, `indexing/`, `search/`, `agent/`

# Design: Fix Image 404

## Context

Hàm `serve_image()` (line 180-186 `api/main.py`) dùng `IMAGES_DIR` để tìm ảnh, nhưng ảnh dataset thực tế nằm ở `DATASET_IMAGES_DIR` (`/app/dataset_images/`). Hàm `_convert_image_path()` đã dùng đúng `DATASET_IMAGES_DIR`.

## Technical Decision

Sửa `serve_image()` để tìm ảnh ở `DATASET_IMAGES_DIR`, với fallback tìm ở `IMAGES_DIR` (phòng trường hợp có ảnh local riêng).

```python
# Trước (bug):
file_path = IMAGES_DIR / filename

# Sau (fix):
file_path = DATASET_IMAGES_DIR / filename
if not file_path.exists():
    file_path = IMAGES_DIR / filename
```

## Risks

- Không có rủi ro. Chỉ thay đổi nơi tìm file ảnh, không ảnh hưởng logic search/agent.

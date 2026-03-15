## 1. Lọc sản phẩm rác (Product Display Filter)

- [x] 1.1 Trong hàm `respond()` (`api/main.py`), thêm logic lọc `valid_products`: duyệt qua `result.products`, bỏ các sản phẩm thiếu `image_path`, file ảnh không tồn tại (qua `_convert_image_path`), hoặc `label` rỗng
- [x] 1.2 Khi `color` rỗng hoặc `None`, hiển thị tiêu đề chỉ gồm `label` (không gắn thêm ` — `)
- [x] 1.3 Khi `caption` rỗng, vẫn hiển thị sản phẩm nhưng bỏ dòng mô tả italic

## 2. Hiển thị ảnh inline (Inline Product Cards)

- [x] 2.1 Xóa logic gửi ảnh dưới dạng message riêng biệt (multi-message kiểu `{"path": ..., "alt_text": ...}`)
- [x] 2.2 Nhúng ảnh sản phẩm trực tiếp trong text markdown bằng thẻ `<img src="/api/images/{filename}" width="220" style="border-radius: 8px; margin-bottom: 15px;" />`
- [x] 2.3 Nâng giới hạn caption hiển thị từ 100 lên 150 ký tự

## 3. Kiểm tra & Rebuild

- [x] 3.1 Rebuild Docker image (`docker compose build fashion-api`) và restart service
- [x] 3.2 Test UI với các query: "áo thun đỏ", "Shoes", "Black jacket" — xác nhận không còn dòng rỗng, ảnh inline gắn liền text
- [x] 3.3 Test edge case: query trả 0 sản phẩm hợp lệ → UI chỉ hiển thị text reply, không có section "Sản phẩm tìm thấy"

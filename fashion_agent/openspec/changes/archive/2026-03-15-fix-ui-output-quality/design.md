## Context

Fashion Agent sử dụng Gradio `gr.Chatbot` để hiển thị kết quả tìm kiếm. Hiện tại, hàm `respond()` trong `api/main.py` render kết quả theo 2 khối tách biệt:
1. Một message text chứa danh sách sản phẩm (label, color, caption)
2. Nhiều message riêng biệt, mỗi message chứa 1 ảnh (dạng `{"path": ..., "alt_text": ...}`)

**Vấn đề:** Khi search engine trả 6 kết quả nhưng một số bị thiếu `caption`, `color`, hoặc `image_path` không tồn tại, UI vẫn render tất cả → xuất hiện các dòng rỗng và ảnh rời rạc không map được với text.

**File ảnh hưởng duy nhất:** `api/main.py` (hàm `respond()` và `_convert_image_path()`).

## Goals / Non-Goals

**Goals:**
- Lọc bỏ sản phẩm rác (thiếu ảnh hoặc thiếu label) trước khi render
- Hiển thị ảnh sản phẩm inline ngay bên dưới text mô tả từng sản phẩm (dạng card)
- Chỉ output N sản phẩm hợp lệ (N ≤ top_k), không pad thêm
- Bỏ hiển thị `— ` khi color rỗng
- Nâng giới hạn caption hiển thị lên 150 ký tự

**Non-Goals:**
- Không thay đổi logic search engine hoặc agent
- Không thay đổi API response format (`/api/chat`)
- Không redesign toàn bộ giao diện Gradio (chỉ fix phần render kết quả)
- Không thay đổi cách lưu dữ liệu trong Qdrant hoặc PostgreSQL

## Decisions

### Decision 1: Lọc sản phẩm ở tầng UI, không phải tầng search

**Chọn:** Lọc tại `respond()` trong `api/main.py`
**Lý do:** Search engine và agent cần nhận đầy đủ kết quả để reasoning (scoring, slot analysis). Tầng UI là nơi thích hợp nhất để quyết định hiển thị hay không.
**Alternative:** Lọc ở search engine → Bỏ vì agent cần thấy toàn bộ kết quả để tính confidence score.

### Decision 2: Dùng HTML `<img>` tag thay vì Gradio multi-message

**Chọn:** Nhúng `<img src="/api/images/{filename}" width="220" />` trực tiếp trong markdown text
**Lý do:** Gradio markdown hỗ trợ HTML tags. Cách này cho phép ảnh nằm liền kề với text mô tả, tạo thành product card hoàn chỉnh trong 1 message duy nhất.
**Alternative:** Giữ multi-message (text + images riêng) → Bỏ vì không thể map ảnh với text tương ứng.

### Decision 3: Điều kiện lọc sản phẩm

Sản phẩm bị **loại bỏ** khi thỏa BẤT KỲ điều kiện nào:
1. `image_path` rỗng hoặc `None`
2. File ảnh không tồn tại trong container (qua `_convert_image_path`)
3. `label` rỗng hoặc `None`

Sản phẩm **vẫn hiển thị** khi:
- `caption` rỗng (hiển thị card không có mô tả)
- `color` rỗng (bỏ phần `— color` trong title)

## Risks / Trade-offs

- **[Risk] Ảnh inline có thể không render trong một số phiên bản Gradio cũ** → Mitigation: Đã test với Gradio 4.x, hoạt động ổn. Nếu lỗi, fallback về text-only.
- **[Risk] Mất sản phẩm hợp lệ do lọc quá chặt** → Mitigation: Chỉ lọc khi thiếu `image_path` hoặc `label`, không lọc theo `caption`/`color`.
- **[Trade-off] Một message text dài vs nhiều message nhỏ** → Chấp nhận 1 message dài hơn để đổi lấy layout product card gọn gàng và dễ đọc.

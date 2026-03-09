## Why

Hiện tại, Clarification Gate chỉ dựa vào `confidence` score do Gemini tự đánh giá (threshold < 0.6). Điều này dẫn đến 2 vấn đề:

1. **Search quá sớm**: Query như "tìm áo trắng" (confidence 0.7) → search ngay → kết quả quá rộng, thiếu precision vì không biết user muốn chất liệu gì, dáng gì, phong cách gì.
2. **Không align với dữ liệu index**: Caption đã được sinh theo 4 thuộc tính (Fabric, Silhouette, Construction, Aesthetic), nhưng query từ user thường chỉ chứa 1-2 thuộc tính → text embedding similarity thấp.

Cần chuyển sang **slot-based information completeness** — đếm thông tin cụ thể user cung cấp, hỏi đúng cái thiếu, và chỉ search khi đủ thông tin để đảm bảo precision.

## What Changes

- **Thêm slot extraction** vào intent classifier: extract 6 slots (category, color, fabric, fit, construction, aesthetic) thay vì chỉ filters đơn giản.
- **Thay thế Clarification Gate** bằng slot completeness check: search khi có `category + color + ≥3/4 caption slots`, hỏi thêm khi thiếu.
- **Multi-turn slot merging**: Merge slots qua các turns trong cùng session, hỗ trợ follow-up kế thừa context.
- **Targeted clarification questions**: Hỏi CỤ THỂ slot đang thiếu thay vì câu hỏi chung chung.
- **Xóa hoặc refactor `clarification_gate.py`**: Logic clarification sẽ nằm trong slot completeness check.

## Capabilities

### New Capabilities
- `slot-extraction`: Extract 6 thông tin slots từ user query (category, color, fabric, fit, construction, aesthetic) sử dụng Gemini LLM.
- `slot-completeness`: Tính completeness score từ extracted slots, quyết định search hay hỏi thêm. Threshold: category + color + 3/4 caption slots.
- `multi-turn-slot-merge`: Merge slots qua các conversation turns, cho phép follow-up kế thừa slots từ turns trước.

### Modified Capabilities
- (none — không có existing specs nào bị ảnh hưởng ở level requirements)

## Impact

- **`agent/intent_classifier.py`**: Mở rộng `ClassifiedIntent` model và prompt để extract 6 slots thay vì filters đơn giản.
- **`agent/clarification_gate.py`**: Refactor hoặc xóa — logic chuyển sang slot completeness check.
- **`agent/fashion_agent.py`**: Thay đổi flow trong `chat()` — thay confidence gate bằng slot check, thêm multi-turn slot merging.
- **`agent/memory.py`**: Có thể cần thêm function store/retrieve accumulated slots per session.
- **API contract**: Không thay đổi — `ChatRequest`/`ChatResponse` giữ nguyên.
- **Dependencies**: Không thêm dependency mới.

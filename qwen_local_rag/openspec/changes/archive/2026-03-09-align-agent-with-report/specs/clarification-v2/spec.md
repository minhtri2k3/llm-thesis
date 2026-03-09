## ADDED Requirements

### Requirement: LLM-based clarification thay rule-based
Khi cần clarification, system SHALL dùng Gemini để sinh câu hỏi phù hợp context thay vì dùng hardcoded strings.

#### Scenario: Câu hỏi dynamic
- **WHEN** user gửi "tìm đồ cho cuối tuần" (unclear, confidence 0.4)
- **THEN** LLM sinh câu hỏi cụ thể: "Bạn muốn tìm trang phục đi chơi cuối tuần hay đồ casual ở nhà? Có màu sắc nào bạn thích không?"

#### Scenario: Câu hỏi dựa trên context
- **WHEN** user vừa tìm áo sơ mi, giờ gửi "cái khác"
- **THEN** LLM hỏi: "Bạn muốn tìm áo sơ mi khác về màu sắc, kiểu dáng, hay loại trang phục hoàn toàn khác?"

### Requirement: Confidence-triggered clarification
Clarification gate SHALL được trigger khi `confidence < 0.6` HOẶC `intent == "unclear"`, thay vì dùng keyword matching.

#### Scenario: Low confidence triggers
- **WHEN** intent classifier trả về confidence = 0.45 cho bất kỳ intent nào
- **THEN** clarification gate kích hoạt, sinh câu hỏi

#### Scenario: High confidence passes through
- **WHEN** intent classifier trả về confidence = 0.85
- **THEN** clarification gate KHÔNG kích hoạt, tiếp tục flow bình thường

### Requirement: Out-of-scope rejection
Khi `intent == "out_of_scope"`, system SHALL từ chối lịch sự và gợi ý quay lại domain thời trang.

#### Scenario: Từ chối ngoài domain
- **WHEN** user gửi "cho tôi công thức nấu phở"
- **THEN** agent trả lời: "Xin lỗi, tôi chỉ hỗ trợ tìm kiếm thời trang. Bạn muốn tìm trang phục gì không?"

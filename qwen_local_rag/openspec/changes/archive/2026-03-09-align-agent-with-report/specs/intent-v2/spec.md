## ADDED Requirements

### Requirement: 5 intent types với confidence score
Intent classifier SHALL phân loại query vào 1 trong 5 intents: `text_search`, `outfit_request`, `follow_up`, `out_of_scope`, `unclear`. Kèm theo confidence score 0.0–1.0.

#### Scenario: Search với confidence cao
- **WHEN** user gửi "tìm áo sơ mi trắng nam"
- **THEN** trả về `{"intent": "text_search", "confidence": 0.95, ...}`

#### Scenario: Follow-up từ context trước
- **WHEN** user vừa hỏi về áo sơ mi, giờ gửi "còn màu xanh thì sao?"
- **THEN** trả về `{"intent": "follow_up", "confidence": 0.85, ...}`

#### Scenario: Out of scope
- **WHEN** user gửi "thời tiết hôm nay thế nào?"
- **THEN** trả về `{"intent": "out_of_scope", "confidence": 0.9, ...}`

#### Scenario: Unclear intent
- **WHEN** user gửi "tìm đồ đẹp"
- **THEN** trả về `{"intent": "unclear", "confidence": 0.4, ...}`

### Requirement: History-aware classification
Intent prompt SHALL nhận 4 messages gần nhất từ conversation history để support follow_up detection.

#### Scenario: Phát hiện follow-up nhờ history
- **WHEN** history có `["tìm áo sơ mi trắng", "đây là 3 áo sơ mi..."]` và user gửi "rẻ hơn có không?"
- **THEN** classifier nhận ra đây là follow_up, trả về context từ câu trước

#### Scenario: Không có history
- **WHEN** session mới, history trống
- **THEN** classifier vẫn hoạt động bình thường, classify dựa trên query alone

### Requirement: Few-shot examples trong prompt
Intent prompt SHALL chứa ít nhất 1 ví dụ cho mỗi intent type (5 ví dụ tổng cộng).

#### Scenario: Prompt format
- **WHEN** classify_intent() được gọi
- **THEN** prompt gửi đến Gemini chứa 5 few-shot examples, mỗi cái map 1 intent

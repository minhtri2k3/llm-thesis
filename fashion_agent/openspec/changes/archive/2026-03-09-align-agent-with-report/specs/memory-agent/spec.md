## ADDED Requirements

### Requirement: liked_items tracking trong user_sessions
System SHALL lưu danh sách items user đã thích dưới dạng JSONB array trong bảng `user_sessions`.

#### Scenario: User thích một sản phẩm
- **WHEN** user biểu thị thích một sản phẩm (qua phản hồi tích cực)
- **THEN** `image_id` được thêm vào `liked_items` JSONB array của session

#### Scenario: Lấy liked items
- **WHEN** system cần biết user thích gì
- **THEN** query `liked_items` từ `user_sessions` trả về list image_ids

### Requirement: query_history logging
System SHALL log mỗi query của user kèm intent và filters vào `query_history` JSONB array.

#### Scenario: Log query mới
- **WHEN** user gửi query "tìm áo sơ mi trắng" với intent="search", filters={"color": "white", "category": "Shirt"}
- **THEN** entry `{"query": "tìm áo sơ mi trắng", "intent": "search", "filters": {...}, "timestamp": "..."}` được append vào `query_history`

#### Scenario: Query history limit
- **WHEN** `query_history` vượt quá 100 entries
- **THEN** giữ 100 entries mới nhất

### Requirement: get_preferences() tổng hợp sở thích
Hàm `get_preferences()` SHALL phân tích `liked_items` và `query_history` để trích xuất top categories, colors, và styles ưa thích.

#### Scenario: User có history
- **WHEN** user đã search 5 lần với color="white" và 3 lần với color="navy"
- **THEN** `get_preferences()` trả về `{"preferred_colors": ["white", "navy"], "preferred_categories": [...]}`

#### Scenario: User mới (không có history)
- **WHEN** session mới, query_history và liked_items trống
- **THEN** `get_preferences()` trả về dict trống `{}`

### Requirement: DB schema migration
System SHALL thêm cột `liked_items` JSONB và `query_history` JSONB vào bảng `user_sessions` nếu chưa tồn tại.

#### Scenario: Migration chạy lần đầu
- **WHEN** hàm `init_memory_tables()` được gọi mà `user_sessions` chưa có cột `liked_items`
- **THEN** ALTER TABLE thêm 2 cột JSONB với default `'[]'`

#### Scenario: Migration chạy lại (idempotent)
- **WHEN** `init_memory_tables()` được gọi mà cột đã tồn tại
- **THEN** không lỗi, không thay đổi gì

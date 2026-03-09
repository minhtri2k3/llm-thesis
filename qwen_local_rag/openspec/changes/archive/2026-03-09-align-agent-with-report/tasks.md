## 1. Image Output Pipeline

- [x] 1.1 Thêm env var `DATASET_IMAGES_HOST_PATH` vào `.env` và docker-compose.yml volume mount → `/app/dataset_images:ro`
- [x] 1.2 Thêm constant `DATASET_IMAGES_DIR` vào `api/main.py`, tạo hàm `_convert_image_path(host_path)` extract basename → container path
- [x] 1.3 Sửa hàm `respond()` trong `api/main.py` — sau text response, append thêm messages dạng `{"role": "assistant", "content": {"path": container_path, "alt_text": label + color}}` cho mỗi product có ảnh
- [x] 1.4 Xử lý graceful degradation: nếu file ảnh không tồn tại trong container, bỏ qua và chỉ hiển thị text
- [x] 1.5 Test: rebuild container, gửi query search, verify ảnh hiển thị trong Gradio chat

## 2. Intent Classifier v2

- [x] 2.1 Cập nhật `ClassifiedIntent` dataclass — thêm field `confidence: float = 0.0`
- [x] 2.2 Viết lại `INTENT_PROMPT` — 5 intents (`text_search`, `outfit_request`, `follow_up`, `out_of_scope`, `unclear`), thêm confidence 0.0–1.0, thêm 5 few-shot examples
- [x] 2.3 Sửa `classify_intent()` — nhận thêm param `history: list[Message]`, truyền 4 messages gần nhất vào prompt
- [x] 2.4 Cập nhật `fashion_agent.py` — truyền history vào `classify_intent(query, history=history, api_key=api_key)`
- [x] 2.5 Test: gửi query follow-up, verify intent = "follow_up" và confidence > 0.7

## 3. Clarification Gate v2

- [x] 3.1 Sửa `clarification_gate.py` — thêm hàm `llm_clarify(query, history, confidence, api_key)` dùng Gemini sinh câu hỏi
- [x] 3.2 Thêm logic out-of-scope rejection — khi `intent == "out_of_scope"`, trả response từ chối lịch sự
- [x] 3.3 Sửa `fashion_agent.py` — thay `check_clarification(query)` bằng logic mới: trigger khi `confidence < 0.6` HOẶC `intent == "unclear"`
- [x] 3.4 Test: gửi query vague "tìm đồ đẹp", verify agent hỏi lại câu hỏi dynamic (không phải hardcoded)

## 4. Memory Agent

- [x] 4.1 Sửa `init_memory_tables()` trong `memory.py` — thêm `ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS liked_items JSONB DEFAULT '[]'::jsonb, ADD COLUMN IF NOT EXISTS query_history JSONB DEFAULT '[]'::jsonb`
- [x] 4.2 Thêm hàm `log_query(session_id, query, intent, filters)` — append entry vào `query_history` JSONB
- [x] 4.3 Thêm hàm `add_liked_item(session_id, image_id)` — append image_id vào `liked_items` JSONB
- [x] 4.4 Thêm hàm `get_preferences(session_id) -> dict` — phân tích query_history + liked_items, trả về `{"preferred_colors": [...], "preferred_categories": [...]}`
- [x] 4.5 Gọi `log_query()` trong `fashion_agent.py chat()` sau khi classify intent
- [x] 4.6 Test: gửi 3 queries khác nhau, verify `query_history` JSONB được populate, `get_preferences()` trả về đúng

## 5. ReAct Orchestrator

- [x] 5.1 Tạo tool registry dict `TOOLS = {"search": ..., "memory_enrich": ..., "outfit_hints": ...}` với function signatures
- [x] 5.2 Viết hàm `_plan(query, history, preferences, observations)` — gọi Gemini sinh JSON array tool calls
- [x] 5.3 Viết hàm `_execute_tool(tool_name, args)` — dispatch tool call, trả observation
- [x] 5.4 Implement tool `memory_enrich` — lấy preferences, bổ sung query
- [x] 5.5 Implement tool `outfit_hints` — gọi Gemini sinh gợi ý outfit theo occasion
- [x] 5.6 Viết ReAct loop mới — thay thế simple retry: for iteration 1..8: plan → execute → observe → check stop condition
- [x] 5.7 Thêm fallback logic: sau 4 iterations, hạ relevance threshold -0.2
- [x] 5.8 Tăng `MAX_REACT_ITERATIONS` → 8
- [x] 5.9 Test: gửi query phức tạp "gợi ý outfit đi tiệc", verify reasoning trace có Thought→Action→Observation

## 6. Synthesis Upgrade

- [x] 6.1 Sửa `SYNTHESIS_PROMPT` — thêm section `User preferences: {preferences_text}` inject sở thích
- [x] 6.2 Sửa `_synthesize_response()` — nhận thêm param `preferences: dict`, format vào prompt
- [x] 6.3 Thêm `image_paths` vào output — trả list paths trong AgentResponse
- [x] 6.4 Sửa `fashion_agent.py` — truyền preferences từ memory vào synthesis
- [x] 6.5 Test: verify response có styling suggestion phù hợp sở thích user

## 7. Integration & Verification

- [x] 7.1 Full integration test: chạy Docker, gửi chuỗi queries, verify toàn bộ flow hoạt động
- [x] 7.2 Verify ảnh hiển thị trong Gradio chat
- [x] 7.3 Verify reasoning trace hiển thị (ít nhất là trong API response)
- [x] 7.4 So sánh lại với báo cáo PDF — cập nhật comparison artifact

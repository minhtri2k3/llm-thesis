## Why

Code agent hiện tại là phiên bản đơn giản hóa, thiếu nhiều tính năng mô tả trong báo cáo luận văn (Fashion Agent Report PDF, Chương 5). Bộ não agent cần được align lại với kiến trúc trong báo cáo để: (1) đảm bảo tính nhất quán giữa tài liệu và code, (2) bổ sung các tính năng quan trọng như ReAct loop thực, memory agent, và image output mà hiện tại chưa có.

## What Changes

- **Intent Classifier nâng cấp**: 4 → 5 intents, thêm confidence score 0.0–1.0, truyền conversation history vào prompt, thêm few-shot examples
- **Clarification Gate LLM-based**: Thay thế rule-based keyword matching bằng LLM sinh câu hỏi dynamic, trigger bằng confidence < 0.6
- **Memory Agent đầy đủ**: Thêm `liked_items` JSONB, `query_history` JSONB, `get_preferences()` tổng hợp sở thích, `memory_enrich` tool
- **ReAct Orchestrator thực**: LLM planning với 3 tools (`search`, `memory_enrich`, `outfit_hints`), max 8 iterations, Thought→Action→Observation pattern, fallback threshold
- **Image Output Pipeline**: Mount ảnh dataset vào Docker, convert image_path, Gradio render ảnh sản phẩm trong chat
- **Synthesis nâng cấp**: Inject user preferences vào prompt, trả image_paths cho UI, hiển thị reasoning trace

## Capabilities

### New Capabilities
- `image-output`: Pipeline hiển thị ảnh sản phẩm từ search results trong Gradio Chatbot — Docker volume mount, path conversion, gr.Gallery/file dict rendering
- `react-orchestrator`: True ReAct loop với LLM planning, tool registry (search/memory_enrich/outfit_hints), max 8 iterations, Thought→Action→Observation trace, fallback logic
- `memory-agent`: Hệ thống tracking sở thích người dùng — liked_items, query_history JSONB, preference extraction, memory enrichment tool
- `intent-v2`: Intent classification 5 loại với confidence score, history-aware prompt, few-shot examples
- `clarification-v2`: LLM-based clarification gate thay thế rule-based, confidence-triggered, out-of-scope rejection

### Modified Capabilities
_(Không có specs cũ — tất cả là capabilities mới)_

## Impact

- **Files thay đổi**: `agent/fashion_agent.py`, `agent/intent_classifier.py`, `agent/clarification_gate.py`, `agent/memory.py`, `api/main.py`, `docker-compose.yml`
- **Database schema**: ALTER TABLE `user_sessions` thêm `liked_items` JSONB, `query_history` JSONB
- **Docker**: Thêm volume mount cho kaggle dataset images
- **Dependencies**: Không thêm dependency mới (đã có `google-generativeai`, `gradio`, `psycopg2`)
- **API**: Response format mở rộng (thêm image_paths, reasoning trace)
- **Breaking changes**: Không — tất cả đều backward-compatible, mở rộng feature

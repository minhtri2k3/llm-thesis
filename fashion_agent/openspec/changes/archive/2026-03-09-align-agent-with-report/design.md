## Context

Fashion Agent là hệ thống RAG tư vấn thời trang chạy trên Docker (FastAPI + Gradio + PostgreSQL + Qdrant). Code hiện tại là phiên bản đơn giản hóa so với kiến trúc mô tả trong báo cáo luận văn (Chương 5). Cần align code với báo cáo để đảm bảo tính nhất quán.

**Current state**: Agent chạy được, search hoạt động, nhưng thiếu: ReAct orchestrator thực, memory tracking, image display, LLM-based clarification, và confidence score.

**Constraints**: Chạy trên M1 Mac 16GB RAM. Dùng Gemini 2.5 Flash (API). Docker Compose stack hiện có.

## Goals / Non-Goals

**Goals:**
- Agent tuân thủ kiến trúc Chương 5 của báo cáo PDF
- Intent classifier trả 5 intents + confidence score + history-aware
- ReAct orchestrator thực với LLM planning + 3 tools
- Memory agent track sở thích người dùng (liked_items, query_history, preferences)
- Clarification gate LLM-based thay rule-based
- Gradio UI hiển thị ảnh sản phẩm từ search results
- Synthesis prompt inject user preferences

**Non-Goals:**
- Thay đổi search pipeline (BM25 + Vector + RRF + Reranker giữ nguyên)
- Thay đổi embedding model (Marqo-FashionSigLIP giữ nguyên)
- Thêm feedback system (agent_feedback table — để sau)
- Chuyển sang Gemini 2.5 Pro (giữ Flash cho chi phí thấp)
- Triển khai production / Cloudflare Tunnel

## Decisions

### 1. Image Access: Mount kaggle cache thay vì copy ảnh

**Chọn**: Mount `/Users/letri/.cache/kagglehub/.../images_compressed` → `/app/dataset_images:ro` trong docker-compose.yml

**Thay vì**: Copy ~5000 ảnh vào `./images/` hoặc serve qua API endpoint riêng

**Lý do**: Không duplicate dữ liệu (~2GB), không cần cập nhật image_path trong DB/Qdrant. Chỉ cần convert path tại runtime trong respond().

### 2. Gradio Image Display: Sử dụng nhiều assistant messages

**Chọn**: Trả text response + từng ảnh là file path dict `{"path": ..., "alt_text": ...}`

**Thay vì**: gr.Gallery() (phức tạp hơn, cần custom component)

**Lý do**: Gradio 6.x Chatbot hỗ trợ native file path dict. Đơn giản, không cần custom JS. Mỗi ảnh có caption riêng.

### 3. ReAct Loop: Tool Registry pattern

**Chọn**: Dict-based tool registry `{"search": fn, "memory_enrich": fn, "outfit_hints": fn}`. LLM sinh JSON array chọn tool + args. Max 8 iterations.

**Thay vì**: Hard-coded if/else chain

**Lý do**: Extensible — dễ thêm tool mới. Tuân thủ ReAct pattern trong báo cáo. LLM tự quyết định tool nào gọi.

### 4. Memory: ALTER TABLE thay vì recreate

**Chọn**: `ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS liked_items JSONB DEFAULT '[]', ADD COLUMN IF NOT EXISTS query_history JSONB DEFAULT '[]'`

**Thay vì**: DROP + CREATE lại table

**Lý do**: Giữ sessions hiện có. Backward-compatible.

### 5. Intent Classifier: Giữ Gemini Flash, thêm structured output

**Chọn**: Thêm fields `confidence`, `follow_up`, `out_of_scope` vào prompt. Truyền 4 messages gần nhất làm context.

**Thay vì**: Chuyển sang model khác hoặc fine-tune

**Lý do**: Gemini Flash đủ cho intent classification. Prompt engineering là cách nhanh nhất.

### 6. Clarification: LLM sinh câu hỏi dựa trên context

**Chọn**: Khi `confidence < 0.6` hoặc `intent == "unclear"`, gọi Gemini sinh câu hỏi clarification phù hợp context.

**Thay vì**: Giữ rule-based

**Lý do**: Báo cáo yêu cầu LLM-based. Dynamic questions tốt hơn hardcoded strings.

## Risks / Trade-offs

- **[Latency tăng]** ReAct loop tối đa 8 iterations × Gemini API call → có thể chậm. → *Mitigation*: Timeout mỗi iteration 10s. Early exit khi kết quả đủ tốt.
- **[Gemini API cost]** Nhiều call hơn (plan + clarify + synthesize). → *Mitigation*: Dùng Flash (rẻ). Cache intent results trong session.
- **[Image path fragile]** Phụ thuộc vào kaggle cache path cụ thể trên host. → *Mitigation*: Dùng env var `DATASET_IMAGES_DIR` để cấu hình mount path.
- **[Memory schema migration]** ALTER TABLE trên DB đang chạy. → *Mitigation*: `ADD COLUMN IF NOT EXISTS` — safe, idempotent.
- **[LLM planning instability]** Gemini có thể sinh tool calls không hợp lệ. → *Mitigation*: Validate JSON output, fallback sang direct search nếu parsing fails.

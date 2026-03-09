## Context

Fashion Agent hiện dùng Clarification Gate đơn giản: nếu `confidence < 0.6` (do Gemini tự đánh giá) thì hỏi lại, ngược lại search ngay. Điều này không tận dụng được cấu trúc caption đã index (4 thuộc tính: Fabric, Silhouette, Construction, Aesthetic) và dẫn đến search với query thiếu thông tin → precision thấp.

**Current flow:**
```
query → classify_intent(confidence) → if < 0.6 → clarify (generic)
                                    → if ≥ 0.6 → search ngay
```

**Proposed flow:**
```
query → extract_slots(6 slots) → if đủ (cat + color + 3/4 caption) → search
                                → if thiếu → hỏi ĐÚNG slot thiếu → merge → loop
```

## Goals / Non-Goals

**Goals:**
- Extract 6 information slots từ user query: category, color, fabric, fit, construction, aesthetic
- Search chỉ khi đạt threshold: `has(category) AND has(color) AND caption_slots ≥ 3`
- Nếu user mô tả đủ từ câu đầu → search ngay, không hỏi thừa
- Nếu thiếu → hỏi targeted questions chỉ về slots đang thiếu
- Multi-turn slot merging: theo dõi slots qua các turns, follow-up kế thừa context
- Align query structure với caption structure đã index để tối đa text embedding similarity

**Non-Goals:**
- Không thay đổi search pipeline (hybrid search, RRF, reranker vẫn giữ nguyên)
- Không thay đổi caption generation hay indexing pipeline
- Không thêm slot "price" hay "brand" (dataset không có)
- Không thay đổi API contract (ChatRequest/ChatResponse)
- Không xử lý outfit_request bằng slot system (giữ flow hiện tại)

## Decisions

### Decision 1: 6 Slots aligned với Caption + Metadata

**Chosen:** 6 slots = category (from label) + color (from color field) + 4 caption properties (fabric, fit, construction, aesthetic)

**Why:** Caption được sinh bởi prompt focus 4 thuộc tính. Text embedding content = `label + color + caption`. Nếu query cũng chứa các thuộc tính này → vector similarity cao nhất. Đây là direct alignment giữa query và index.

**Alternatives considered:**
- *Weighted scoring (35%, 25%, 20%, 20%)*: Phức tạp hơn, cần tune weights, nhưng user muốn logic đơn giản "đủ thì search, thiếu thì hỏi"
- *Only category + color*: Quá ít thông tin, không tận dụng caption embeddings

### Decision 2: Extraction bằng Gemini trong classify_intent

**Chosen:** Mở rộng prompt của `classify_intent()` để extract thêm 4 caption slots (fabric, fit, construction, aesthetic) cùng lúc với intent + filters.

**Why:** Tiết kiệm 1 LLM call — không cần gọi thêm function riêng. Intent classifier đã nhận query + history, chỉ cần mở rộng output schema.

**Alternatives considered:**
- *Separate slot extractor function*: Thêm 1 LLM call/request → tăng latency + cost
- *Regex/keyword extraction*: Không đủ thông minh cho ngôn ngữ tự nhiên (e.g., "dáng ôm" → slim fit)

### Decision 3: Threshold = category + color + 3/4 caption slots

**Chosen:** Search khi: `has(category) AND has(color) AND count_filled(fabric, fit, construction, aesthetic) >= 3`

**Why:**
- Category + color là 2 field metadata chính (dùng cho BM25 keyword matching)
- 3/4 caption slots đảm bảo rich text cho embedding similarity, cho phép bỏ 1 slot
- User nói "không cần biết construction detail" → vẫn search được

### Decision 4: Multi-turn slot merging bằng session accumulated_slots

**Chosen:** Lưu accumulated slots trong `chat()` function qua các iterations. Khi user trả lời follow-up, merge slots mới vào accumulated slots, rồi re-check threshold.

**Why:** Simple in-memory merge, không cần thêm DB schema. Slots chỉ live trong 1 session conversation flow.

**Alternatives considered:**
- *Lưu slots vào PostgreSQL session table*: Overkill cho scope này, slots chỉ cần tồn tại trong conversation flow
- *Dùng memory.get_preferences()*: Khác concept — preferences là long-term, slots là per-request

### Decision 5: Hỏi gộp slots thiếu (1 câu hỏi)

**Chosen:** Khi thiếu slots, gộp tất cả missing slots vào 1 câu hỏi tự nhiên. Không hỏi từng slot riêng.

**Why:** Giảm số turns, UX tốt hơn. User có thể trả lời 1 phần → merge → hỏi tiếp nếu vẫn thiếu.

### Decision 6: Chỉ áp dụng cho text_search intent

**Chosen:** Slot-based clarification chỉ áp dụng khi `intent == "text_search"`. Các intent khác (outfit_request, follow_up, out_of_scope) giữ flow hiện tại.

**Why:** `outfit_request` cần occasion + style hơn là category + color. `follow_up` kế thừa slots từ turn trước nên thường đã đủ. Logic tách biệt, dễ maintain.

## Risks / Trade-offs

- **[Tăng turns cho query đơn giản]** → User nói "tìm áo trắng" giờ sẽ bị hỏi thêm thay vì search ngay. Mitigation: Kết quả chính xác hơn nên user chấp nhận 1-2 turn thêm.

- **[Gemini extraction quality]** → LLM có thể extract sai slot (e.g., "cotton" → aesthetic thay vì fabric). Mitigation: Dùng structured output (JSON schema) với descriptions rõ ràng cho từng slot.

- **[Follow-up slot inheritance phức tạp]** → "còn màu khác?" cần biết clear slot nào (color) và giữ slot nào (category, fabric...). Mitigation: Merge logic: slot mới override, slot cũ giữ nguyên.

- **[Latency tăng do multi-turn]** → Mỗi turn thêm 1 LLM call (re-classify). Mitigation: Max 3 clarification turns, sau đó search với whatever có.

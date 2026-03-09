## 1. Data Models

- [x] 1.1 Tạo `ExtractedSlots` dataclass trong `agent/intent_classifier.py` với 6 fields: category, color, fabric, fit, construction, aesthetic (tất cả Optional[str])
- [x] 1.2 Thêm field `extracted_slots: ExtractedSlots` vào `ClassifiedIntent` dataclass

## 2. Slot Extraction (Intent Classifier)

- [x] 2.1 Mở rộng prompt của `classify_intent()` để yêu cầu Gemini trả thêm 6 slots trong JSON output
- [x] 2.2 Parse response JSON mới để populate `ExtractedSlots` object
- [x] 2.3 Thêm error handling: nếu slot parsing fail → fallback về slots rỗng (all null)

## 3. Slot Completeness Check

- [x] 3.1 Tạo function `check_slot_completeness(slots: ExtractedSlots) -> tuple[bool, list[str]]` trả về (is_complete, missing_slots)
- [x] 3.2 Implement logic: complete khi has(category) AND has(color) AND count_filled(fabric, fit, construction, aesthetic) >= 3
- [x] 3.3 Tạo function `generate_targeted_question(missing_slots: list[str], history: list) -> str` dùng Gemini để hỏi tự nhiên về slots thiếu

## 4. Multi-Turn Slot Merging

- [x] 4.1 Tạo function `merge_slots(accumulated: ExtractedSlots, new: ExtractedSlots) -> ExtractedSlots` — slot mới override slot cũ, slot null giữ nguyên
- [x] 4.2 Tạo function `should_reset_slots(accumulated: ExtractedSlots, new: ExtractedSlots) -> bool` — reset khi category thay đổi hoàn toàn (new topic)

## 5. Agent Flow Integration

- [x] 5.1 Sửa `chat()` trong `fashion_agent.py`: thêm accumulated_slots variable theo dõi qua conversation
- [x] 5.2 Thêm slot completeness check sau intent classification (chỉ cho text_search intent)
- [x] 5.3 Implement clarification loop: nếu thiếu → hỏi → user trả lời → re-classify → merge → check lại
- [x] 5.4 Thêm max clarification turns counter (max 3), sau 3 turns → search với whatever có
- [x] 5.5 Follow-up intent: merge slots mới với accumulated slots trước khi check completeness

## 6. Cleanup

- [x] 6.1 Đánh giá `clarification_gate.py`: giữ lại cho non-text_search intents hoặc xóa nếu không cần
- [x] 6.2 Cập nhật refined_query: compose từ filled slots (e.g., "white cotton slim fit formal shirt") thay vì chỉ dựa vào Gemini refined_query

## 7. Testing & Verification

- [x] 7.1 Test kịch bản: query đầy đủ → search ngay (0 clarification turns)
- [x] 7.2 Test kịch bản: query thiếu → hỏi 1-2 lần → search
- [x] 7.3 Test kịch bản: follow-up kế thừa slots → search ngay
- [x] 7.4 Test kịch bản: new topic → reset slots → hỏi lại
- [x] 7.5 Test kịch bản: max 3 turns → force search
- [x] 7.6 Test edge case: Gemini trả slots sai format → fallback graceful

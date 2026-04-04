## ADDED Requirements

### Requirement: Language detection utility
The system SHALL provide a zero-cost utility function `detect_language(text: str) -> str` that returns `"vi"` when the input contains Vietnamese diacritics or common Vietnamese patterns, and `"en"` otherwise. This function MUST NOT make any LLM call.

#### Scenario: Vietnamese text detected
- **WHEN** user message contains characters such as `à á ả ã ạ ă â ê ô ơ ư đ` or their toned variants
- **THEN** `detect_language()` returns `"vi"`

#### Scenario: English or no-diacritic text detected
- **WHEN** user message contains only ASCII characters or non-Vietnamese diacritics
- **THEN** `detect_language()` returns `"en"`

#### Scenario: Empty or whitespace input
- **WHEN** text is empty or whitespace-only
- **THEN** `detect_language()` returns `"en"` as the safe default

---

### Requirement: Bilingual FALLBACK_QUESTION
The system SHALL provide a Vietnamese and English version of `FALLBACK_QUESTION`. The clarification gate MUST select the correct version based on `detect_language()` applied to the user's query before returning the fallback string.

#### Scenario: Vietnamese user hits fallback
- **WHEN** the LLM clarification call fails and the user's query is Vietnamese
- **THEN** the returned fallback question is written in Vietnamese (e.g., "Bạn có thể mô tả cụ thể hơn...")

#### Scenario: English user hits fallback
- **WHEN** the LLM clarification call fails and the user's query is English or ambiguous
- **THEN** the returned fallback question is written in English (existing text)

---

### Requirement: Bilingual slot-completeness clarification templates
The system SHALL provide Vietnamese equivalents for all entries in `SLOT_TEMPLATES` and `COMBO_TEMPLATES`. Template selection MUST be based on `detect_language()` applied to the last user message passed to `build_template_question()`.

#### Scenario: Vietnamese user triggers slot clarification
- **WHEN** slot completeness check fails and the user is Vietnamese
- **THEN** the clarification question is written in Vietnamese with appropriate emoji and phrasing

#### Scenario: English user triggers slot clarification
- **WHEN** slot completeness check fails and the user is English
- **THEN** the clarification question text is unchanged from existing English templates

---

### Requirement: Language-aware fixed agent response strings
All hardcoded response strings in `fashion_agent.py` — `OUT_OF_SCOPE_RESPONSE`, messages inside `_handle_reject()`, `_handle_confirm()`, `_handle_view_selections()`, and `_handle_product_select()` — MUST be language-aware. Each SHALL have a Vietnamese and English variant, selected at runtime based on `detect_language()` applied to the current user query.

#### Scenario: Vietnamese user is out-of-scope
- **WHEN** intent is `out_of_scope` and user's message is Vietnamese
- **THEN** the agent responds in Vietnamese (e.g., "Xin lỗi, tôi chỉ hỗ trợ tìm kiếm thời trang...")

#### Scenario: English user is out-of-scope
- **WHEN** intent is `out_of_scope` and user's message is English
- **THEN** the agent responds in English (existing text)

#### Scenario: Vietnamese confirm message
- **WHEN** user confirms a selection and their last message is Vietnamese
- **THEN** save confirmation message is in Vietnamese (e.g., "💾 **Đã lưu {n} sản phẩm!**")

#### Scenario: Vietnamese cancel message
- **WHEN** user rejects a selection and their last message is Vietnamese
- **THEN** cancellation message is in Vietnamese (e.g., "❌ Đã hủy lựa chọn...")

---

### Requirement: Language-aware synthesis CTA
The synthesis prompt MUST inject a pre-selected CTA string in the correct user language as a format variable `{cta_example}`, rather than asking the LLM to adapt a hardcoded English example. The Python layer SHALL select the CTA string before the LLM call using `detect_language()`.

#### Scenario: Vietnamese CTA injection
- **WHEN** user message is Vietnamese and synthesis prompt is built
- **THEN** `cta_example` contains "👉 Nhập số từ 1 đến {num_results} để chọn sản phẩm bạn yêu thích!"

#### Scenario: English CTA injection
- **WHEN** user message is English and synthesis prompt is built
- **THEN** `cta_example` contains "👉 Type a number (1-{num_results}) to select your favorite!"

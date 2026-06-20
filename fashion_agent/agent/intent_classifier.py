"""Phân loại ý định người dùng và trích xuất slot bằng Gemini LLM.

Mục đích tổng thể:
- File này là bước LLM đầu tiên trong pipeline chat.
- Nó gửi câu hỏi của người dùng và lịch sử hội thoại gần nhất sang Gemini.
- Gemini trả về JSON gồm intent, confidence, filters, refined_query,
  selected_numbers, và 6 slot thời trang.
- File này chịu trách nhiệm parse JSON thô từ LLM thành các dataclass Python an toàn.
- Các file phía sau, ví dụ clarification_gate.py, nên nhận object đã parse sẵn
  thay vì xử lý trực tiếp JSON thô từ LLM.

Các object và method chính:
- ExtractedSlots: lưu 6 slot thời trang được trích xuất từ query:
  category, color, fabric, fit, construction, và aesthetic. Nó cũng lưu
  selected_numbers cho các câu follow-up chọn sản phẩm.
- ExtractedSlots.filled_count(): đếm số slot trong 6 slot đang có giá trị.
  Logic phía sau dùng số này để ước lượng query của người dùng đã cụ thể chưa.
- ExtractedSlots.caption_slots_filled(): chỉ đếm các slot cấp caption:
  fabric, fit, construction, và aesthetic. Các slot này gần với caption sản phẩm.
- ExtractedSlots._all_values(): helper nội bộ trả về danh sách 6 slot để tái sử dụng
  logic đếm một cách nhất quán.
- ClassifiedIntent: output đã chuẩn hóa từ Gemini. Nó gom intent, confidence,
  filters, refined_query, slots đã parse, và token usage.
- _parse_slots(): chuyển các key JSON của Gemini như slot_category và slot_color
  thành object ExtractedSlots. Nếu parse lỗi, nó trả về ExtractedSlots rỗng.
- classify_intent(): function public chính. Nó tạo prompt, gọi Gemini, parse JSON,
  lấy token usage, và trả về ClassifiedIntent. Nếu parse JSON lỗi, nó fallback
  về text_search an toàn với confidence 0.5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agent.utils import parse_llm_json
from agent.utils import format_history_text
from agent.prompts import INTENT_PROMPT
from shared.llm import get_model


@dataclass
class ExtractedSlots:
    """Lưu 6 slot thời trang trích xuất từ query người dùng.

    category và color là metadata chính; fabric, fit, construction và aesthetic
    là các slot mô tả chi tiết hơn phục vụ truy vấn và caption.
    """

    category: Optional[str] = None  # e.g., "Shirt", "Dress", "Pants"
    color: Optional[str] = None  # e.g., "white", "navy blue"
    fabric: Optional[str] = None  # e.g., "cotton", "silk", "denim"
    fit: Optional[str] = None  # e.g., "slim fit", "oversized", "A-line"
    construction: Optional[str] = None  # e.g., "point collar", "zip closure"
    aesthetic: Optional[str] = None  # e.g., "casual", "formal", "minimalist"
    selected_numbers: list[int] = field(default_factory=list)  # e.g., [1, 3] for product selection

    def filled_count(self) -> int:
        """Đếm số slot đang có giá trị."""
        return sum(1 for v in self._all_values() if v)

    def caption_slots_filled(self) -> int:
        """Đếm số slot thuộc phần mô tả caption."""
        return sum(1 for v in [self.fabric, self.fit, self.construction, self.aesthetic] if v)

    def _all_values(self) -> list[Optional[str]]:
        """Trả về toàn bộ 6 slot để tái sử dụng logic đếm."""
        return [self.category, self.color, self.fabric, self.fit, self.construction, self.aesthetic]


@dataclass
class ClassifiedIntent:
    """Kết quả classify intent đã được chuẩn hóa từ Gemini."""

    intent: str  # "text_search", "outfit_request", "follow_up", "out_of_scope", "unclear"
    confidence: float  # 0.0 – 1.0
    filters: dict  # extracted filters like {category, color, style}
    refined_query: str  # cleaned/preprocessed query for search
    extracted_slots: ExtractedSlots = field(default_factory=ExtractedSlots)
    input_tokens: int = 0   # from response.usage_metadata
    output_tokens: int = 0  # from response.usage_metadata


def _parse_slots(data: dict) -> ExtractedSlots:
    """Chuyển JSON thô từ Gemini thành `ExtractedSlots` an toàn."""
    try:
        # Parse selected_numbers safely
        raw_numbers = data.get("selected_numbers", [])
        if isinstance(raw_numbers, list):
            selected_numbers = [int(n) for n in raw_numbers if isinstance(n, (int, float))]
        else:
            selected_numbers = []

        return ExtractedSlots(
            category=data.get("slot_category") or None,
            color=data.get("slot_color") or None,
            fabric=data.get("slot_fabric") or None,
            fit=data.get("slot_fit") or None,
            construction=data.get("slot_construction") or None,
            aesthetic=data.get("slot_aesthetic") or None,
            selected_numbers=selected_numbers,
        )
    except Exception:
        return ExtractedSlots()


def classify_intent(
    query: str,
    history: list | None = None,
) -> ClassifiedIntent:
    """Phân loại query và trích xuất 6 slot trong một lần gọi LLM."""
    model = get_model()

    history_text = format_history_text(history, limit=4)

    full_prompt = INTENT_PROMPT.format(history_text=history_text) + query
    response = model.generate_content(full_prompt)

    # Extract token usage defensively
    usage = getattr(response, "usage_metadata", None)
    in_tok = getattr(usage, "prompt_token_count", 0) or 0
    out_tok = getattr(usage, "candidates_token_count", 0) or 0

    try:
        data = parse_llm_json(response.text)
        slots = _parse_slots(data)

        return ClassifiedIntent(
            intent=data.get("intent", "text_search"),
            confidence=float(data.get("confidence", 0.5)),
            filters=data.get("filters", {}),
            refined_query=data.get("refined_query", query),
            extracted_slots=slots,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Intent classification parse failed: %s", exc)
        # Fallback: treat as search if classification fails, with empty slots
        return ClassifiedIntent(
            intent="text_search",
            confidence=0.5,
            filters={},
            refined_query=query,
            extracted_slots=ExtractedSlots(),
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

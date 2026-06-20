"""Kiểm tra độ đầy đủ của slot và tạo câu hỏi làm rõ theo mẫu."""

from __future__ import annotations


from agent.intent_classifier import ExtractedSlots


# ---------------------------------------------------------------------------
# Slot Completeness Check
# ---------------------------------------------------------------------------


def check_slot_completeness(
    slots: ExtractedSlots,
) -> tuple[bool, list[str]]:
    """Kiểm tra các slot đã đủ để bắt đầu tìm kiếm hay chưa.

    Ngưỡng tìm kiếm hiện tại:
    - `category` đã có giá trị
    - `color` đã có giá trị
    - ít nhất một trong `fabric` hoặc `fit` đã có giá trị

    `construction` và `aesthetic` là slot bổ sung: hệ thống có thể gợi ý thêm,
    nhưng chúng không chặn truy vấn tìm kiếm.

    Trả về:
        (is_complete, missing_slot_names)
    """
    missing: list[str] = []

    if not slots.category:
        missing.append("category")
    if not slots.color:
        missing.append("color")

    has_fabric_or_fit = bool(slots.fabric) or bool(slots.fit)
    if not has_fabric_or_fit:
        # Report both as missing so the template question covers both
        if not slots.fabric:
            missing.append("fabric")
        if not slots.fit:
            missing.append("fit")

    is_complete = bool(slots.category) and bool(slots.color) and has_fabric_or_fit
    return is_complete, missing


# ---------------------------------------------------------------------------
# Template-based clarification (0 LLM calls)
# ---------------------------------------------------------------------------

# Pre-built template parts — imported from centralized prompts module.
from agent.prompts import SLOT_TEMPLATES, COMBO_TEMPLATES, detect_language, get_template


def build_template_question(
    missing_slots: list[str],
    slots: ExtractedSlots,
    query: str = "",
) -> str:
    """Tạo câu hỏi làm rõ từ template có sẵn mà không cần gọi LLM.

    Hàm chọn template phù hợp nhất theo các slot còn thiếu, rồi chèn các giá trị
    slot đã biết để câu hỏi tự nhiên hơn.

    Tham số:
        missing_slots: Danh sách slot còn thiếu từ `check_slot_completeness`.
        slots: Dữ liệu slot đang tích lũy để điền vào template.
        query: Query gốc của người dùng, dùng để nhận diện ngôn ngữ.

    Trả về:
        Một câu hỏi làm rõ thân thiện bằng ngôn ngữ của người dùng.
    """
    lang = detect_language(query)
    missing_key = frozenset(missing_slots)

    # Try exact match first, then fallback to generic build
    template_str = get_template(COMBO_TEMPLATES, missing_key, lang)
    if template_str:
        # Provide safe fallbacks for format variables
        if lang == "vi":
            category_val = slots.category or "trang phục"
            color_val = slots.color or "màu bạn thích"
        elif lang == "es":
            category_val = slots.category or "ropa"
            color_val = slots.color or "tu color preferido"
        else:
            category_val = slots.category or "clothing"
            color_val = slots.color or "your preferred color"
        return template_str.format(
            category=category_val,
            color=color_val,
        )

    # Generic fallback: list each missing slot individually
    if lang == "vi":
        parts = ["Bạn có thể cho tôi biết thêm không? 💬"]
    elif lang == "es":
        parts = ["¿Podrías contarme un poco más? 💬"]
    else:
        parts = ["Could you tell me a bit more? 💬"]
    for slot in missing_slots:
        label = get_template(SLOT_TEMPLATES, slot, lang) or slot
        parts.append(f"• **{slot.capitalize()}**: {label}")
    return "\n".join(parts)




# ---------------------------------------------------------------------------
# Slot Merging
# ---------------------------------------------------------------------------

def merge_slots(
    accumulated: ExtractedSlots,
    new: ExtractedSlots,
) -> ExtractedSlots:
    """Gộp slot mới vào slot đã tích lũy, ưu tiên giá trị mới nếu có."""
    return ExtractedSlots(
        category=new.category or accumulated.category,
        color=new.color or accumulated.color,
        fabric=new.fabric or accumulated.fabric,
        fit=new.fit or accumulated.fit,
        construction=new.construction or accumulated.construction,
        aesthetic=new.aesthetic or accumulated.aesthetic,
    )


def should_reset_slots(
    accumulated: ExtractedSlots,
    new: ExtractedSlots,
) -> bool:
    """Xác định có cần reset slot hay không khi người dùng đổi chủ đề."""
    if not accumulated.category or not new.category:
        return False
    return (
        new.category.lower().strip() != accumulated.category.lower().strip()
    )


def compose_refined_query_from_slots(slots: ExtractedSlots) -> str:
    """Ghép các slot đã có thành một refined query giàu ngữ cảnh."""
    parts = []
    if slots.color:
        parts.append(slots.color)
    if slots.fabric:
        parts.append(slots.fabric)
    if slots.fit:
        parts.append(slots.fit)
    if slots.construction:
        parts.append(slots.construction)
    if slots.aesthetic:
        parts.append(slots.aesthetic)
    if slots.category:
        parts.append(slots.category)
    return " ".join(parts)

"""Các helper dùng chung cho các mô-đun của Fashion Agent.

- `parse_llm_json`: tách JSON từ phản hồi LLM có thể được bọc trong code fence.
- `fallback_text_response`: tạo câu trả lời text dự phòng khi LLM không khả dụng.
- Các hằng số và helper cho việc kiểm tra category không được hỗ trợ.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


# ---------------------------------------------------------------------------
# Supported clothing categories — must match the 17 distinct label values
# in the fashion_items database table.
# ---------------------------------------------------------------------------

SUPPORTED_CATEGORIES: set[str] = {
    "Blazer", "Blouse", "Body", "Dress", "Hat", "Hoodie", "Longsleeve",
    "Outwear", "Pants", "Polo", "Shirt", "Shoes", "Shorts", "Skirt",
    "T-Shirt", "Top", "Undershirt",
}

_CATEGORY_BY_NORMALIZED: dict[str, str] = {
    category.lower(): category for category in SUPPORTED_CATEGORIES
}
_CATEGORY_BY_NORMALIZED.update({
    "t shirt": "T-Shirt",
    "tshirt": "T-Shirt",
})

CATEGORY_SYNONYMS: dict[str, str] = {
    "trouser": "Pants",
    "trousers": "Pants",
    "slacks": "Pants",
    "jean": "Pants",
    "jeans": "Pants",
    "denim": "Pants",
    "denim pants": "Pants",
    "tee": "T-Shirt",
    "tees": "T-Shirt",
    "t shirt": "T-Shirt",
    "t-shirt": "T-Shirt",
    "tshirt": "T-Shirt",
    "button up": "Shirt",
    "button-up": "Shirt",
    "button down": "Shirt",
    "button-down": "Shirt",
    "dress shirt": "Shirt",
    "jacket": "Outwear",
    "jackets": "Outwear",
    "coat": "Outwear",
    "coats": "Outwear",
    "outerwear": "Outwear",
    "cardigan": "Outwear",
    "cardigans": "Outwear",
    "sweatshirt": "Hoodie",
    "sweatshirts": "Hoodie",
    "sweater": "Longsleeve",
    "sweaters": "Longsleeve",
    "long sleeve": "Longsleeve",
    "long sleeves": "Longsleeve",
    "long-sleeve": "Longsleeve",
    "long-sleeves": "Longsleeve",
    "sneaker": "Shoes",
    "sneakers": "Shoes",
    "boot": "Shoes",
    "boots": "Shoes",
    "heel": "Shoes",
    "heels": "Shoes",
    "shoe": "Shoes",
    "cap": "Hat",
    "caps": "Hat",
    "beanie": "Hat",
    "beanies": "Hat",
    "tank": "Top",
    "tanktop": "Top",
    "tank top": "Top",
    "cami": "Top",
    "camisole": "Top",
    "crop top": "Top",
    "mini skirt": "Skirt",
    "midi skirt": "Skirt",
    "gown": "Dress",
    "gowns": "Dress",
    "short pants": "Shorts",
}

FUZZY_CATEGORY_THRESHOLD = 80


@dataclass(frozen=True)
class CategoryNormalization:
    """Kết quả chuẩn hóa category người dùng sang label catalog."""

    raw: str
    category: str = ""
    method: str = "unresolved"
    confidence: float = 0.0
    matched: str = ""

    @property
    def resolved(self) -> bool:
        """Cho biết category đã được resolve thành label chuẩn hay chưa."""
        return bool(self.category)


# Common unsupported items → 2–3 supported alternatives.
# Empty list means no close equivalent exists.
UNSUPPORTED_CATEGORY_SUGGESTIONS: dict[str, list[str]] = {
    "bikini":     ["Body", "Top", "Shorts"],
    "swimsuit":   ["Body", "Shorts"],
    "swimwear":   ["Body", "Shorts", "Top"],
    "jeans":      ["Pants", "Shorts"],
    "denim":      ["Pants", "Shorts"],
    "coat":       ["Outwear", "Blazer"],
    "jacket":     ["Outwear", "Blazer", "Hoodie"],
    "cardigan":   ["Outwear", "Longsleeve"],
    "sweater":    ["Hoodie", "Longsleeve"],
    "suit":       ["Blazer", "Pants"],
    "sneakers":   ["Shoes"],
    "boots":      ["Shoes"],
    "heels":      ["Shoes"],
    "bra":        ["Body", "Undershirt"],
    "underwear":  ["Undershirt", "Body"],
    "pyjamas":    ["Undershirt", "Longsleeve"],
    "lingerie":   ["Body", "Undershirt"],
    "vest":       ["Top", "Undershirt"],
    "crop top":   ["Top", "Blouse"],
    "tank top":   ["Top", "Undershirt"],
    "turtleneck": ["Longsleeve", "Top"],
    "scarf":      ["Hat"],
    "cap":        ["Hat"],
    "bag":        [],
    "watch":      [],
}


def _normalize_category_key(category: str) -> str:
    """Chuẩn hóa category về key đơn giản để so khớp chính xác hơn."""
    normalized = re.sub(r"[^a-z0-9]+", " ", category.strip().lower())
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_category(category: str) -> CategoryNormalization:
    """Chuẩn hóa category người dùng sang label catalog chính thức nếu có thể."""
    raw = (category or "").strip()
    normalized = _normalize_category_key(raw)
    if not normalized:
        return CategoryNormalization(raw=raw)

    canonical = _CATEGORY_BY_NORMALIZED.get(normalized)
    if canonical:
        return CategoryNormalization(
            raw=raw,
            category=canonical,
            method="exact",
            confidence=1.0,
            matched=canonical,
        )

    synonym = CATEGORY_SYNONYMS.get(normalized)
    if synonym:
        return CategoryNormalization(
            raw=raw,
            category=synonym,
            method="synonym",
            confidence=1.0,
            matched=normalized,
        )

    choices = {
        **_CATEGORY_BY_NORMALIZED,
        **CATEGORY_SYNONYMS,
    }
    try:
        from rapidfuzz import fuzz, process
        match = process.extractOne(
            normalized,
            choices.keys(),
            scorer=fuzz.WRatio,
            score_cutoff=FUZZY_CATEGORY_THRESHOLD,
        )
        if match:
            matched_key, score, _ = match
            return CategoryNormalization(
                raw=raw,
                category=choices[matched_key],
                method="fuzzy",
                confidence=score / 100.0,
                matched=matched_key,
            )
    except Exception:
        best_key = ""
        best_score = 0.0
        for choice in choices:
            score = SequenceMatcher(None, normalized, choice).ratio()
            if score > best_score:
                best_key = choice
                best_score = score
        if best_key and best_score >= FUZZY_CATEGORY_THRESHOLD / 100.0:
            return CategoryNormalization(
                raw=raw,
                category=choices[best_key],
                method="fuzzy",
                confidence=best_score,
                matched=best_key,
            )

    return CategoryNormalization(raw=raw)


def expand_category_query_terms(raw_category: str, canonical_category: str) -> list[str]:
    """Tạo các term query gồm category chuẩn và category gốc khi phù hợp."""
    terms: list[str] = []
    raw = (raw_category or "").strip()
    canonical = (canonical_category or "").strip()
    if canonical:
        terms.append(canonical)
    if raw and raw.lower() != canonical.lower():
        terms.append(raw)
    return terms


def _find_category_suggestions(category: str) -> list[str]:
    """Tìm các category được hỗ trợ để gợi ý cho category không hợp lệ."""
    normalized = _normalize_category_key(category)
    if not normalized:
        return []

    resolved = normalize_category(category)
    if resolved.resolved:
        return [resolved.category]

    suggestions = UNSUPPORTED_CATEGORY_SUGGESTIONS.get(normalized)
    if suggestions is not None:
        return suggestions[:3]

    try:
        from rapidfuzz import process
        match = process.extractOne(
            normalized,
            SUPPORTED_CATEGORIES,
            score_cutoff=60,
        )
        if match:
            return [match[0]]
    except Exception:
        pass

    return []


def parse_llm_json(text: str) -> dict[str, Any]:
    """Parse một object JSON từ output thô của LLM.

    Hàm xử lý các kiểu phổ biến:
    - Chuỗi JSON thô
    - JSON bọc trong ```json ... ``` hoặc ``` ... ``` code block
    - Khoảng trắng ở đầu/cuối chuỗi

    Nếu parse thất bại, hàm trả về dict rỗng.
    """
    cleaned = text.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if cleaned.startswith("```"):
        # Remove opening fence (possibly with language tag)
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        # Remove closing fence
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        # If the LLM returned a JSON array, wrap it
        if isinstance(result, list):
            return {"items": result}
    except (json.JSONDecodeError, ValueError):
        pass

    # Last resort: try to find a JSON object in the text
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass

    return {}


def fallback_text_response(products: list) -> str:
    """Tạo câu trả lời text dự phòng để liệt kê sản phẩm.

    Dùng khi LLM tổng hợp không khả dụng. Mỗi product được kỳ vọng có thuộc
    tính `.label` hoặc là dict có khóa `label`.
    """
    if not products:
        return "No matching products found."

    labels: list[str] = []
    for p in products[:5]:
        if hasattr(p, "label"):
            labels.append(p.label)
        elif isinstance(p, dict):
            labels.append(p.get("label", "Unknown"))
        else:
            labels.append(str(p))

    return f"Tìm thấy {len(products)} sản phẩm: {', '.join(labels)}."


def format_history_text(
    history: list | None,
    limit: int = 4,
    truncate: int = 100,
) -> str:
    """Định dạng lịch sử hội thoại thành text để đưa vào prompt.

    Helper dùng chung cho intent classification, clarification gate và
    synthesis context builder, thay cho nhiều đoạn lặp lại.

    Tham số:
        history: Danh sách message object (có `.role` và `.content`).
        limit: Số message gần nhất cần lấy.
        truncate: Số ký tự tối đa cho mỗi message.

    Trả về:
        Text lịch sử đã định dạng, hoặc `No prior conversation.` nếu rỗng.
    """
    if not history:
        return "No prior conversation."

    lines: list[str] = []
    for msg in history[-limit:]:
        role = getattr(msg, "role", "user")
        content = getattr(msg, "content", str(msg))
        lines.append(f"{role}: {content[:truncate]}")
    return "\n".join(lines) if lines else "No prior conversation."

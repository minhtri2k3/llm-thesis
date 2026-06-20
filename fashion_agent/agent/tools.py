"""Các hàm tool được xuất cho các orchestrator ở Mode B và Mode C.

Đây là lớp bao mỏng quanh search engine hiện có. Hàm trả về plain dict thay vì
NodeWithScore để dễ serialize và truyền qua cơ chế function calling của LLM.
"""
from __future__ import annotations

import logging
from typing import Optional

from agent.utils import SUPPORTED_CATEGORIES, _find_category_suggestions

logger = logging.getLogger(__name__)


def run_search_tool(
    query: str,
    top_k: int = 5,
    gender: str = "",
    category: str = "",
    color: str = "",
) -> list[dict]:
    """Chạy tìm kiếm thời trang hybrid và trả về danh sách dict đơn giản.

    Tham số:
        query: Query tìm kiếm tự nhiên bằng ngôn ngữ người dùng.
        top_k: Số kết quả tối đa.
        gender: Bộ lọc giới tính tùy chọn (`male`, `female`, `unisex`, `""`).
        category: Bộ lọc category tùy chọn.
        color: Bộ lọc màu sắc tùy chọn.

    Trả về:
        Danh sách product dict với các khóa `image_id`, `image_path`, `label`,
        `color`, `caption`, `score`. Nếu category không hợp lệ, trả về dict lỗi.
    """
    from search.search_engine import search as hybrid_search

    # ── Safety-net: reject unsupported categories ──────────────────────
    if category and category not in SUPPORTED_CATEGORIES:
        suggestions = _find_category_suggestions(category)
        return [{
            "__error__": "unsupported_category",
            "requested": category,
            "suggestions": suggestions,
        }]

    filters: dict[str, str] = {}
    if gender and gender not in ("", "unisex"):
        filters["gender"] = gender
    if category:
        filters["category"] = category
    if color:
        filters["color"] = color

    try:
        results = hybrid_search(query, top_k=top_k, use_query_expansion=False, filters=filters)
        return [
            {
                "image_id": r.image_id,
                "image_path": r.image_path,
                "label": r.label,
                "color": r.color,
                "caption": r.caption,
                "score": round(r.score, 4),
            }
            for r in results
        ]
    except Exception as exc:
        logger.error("run_search_tool failed: %s", exc)
        return []


def run_recommend_tool(
    style: str = "",
    occasion: str = "",
    gender: str = "",
    top_k: int = 3,
) -> list[dict]:
    """Chạy tìm kiếm gợi ý outfit theo style hoặc dịp sử dụng.

    Hàm ghép một query tổng hợp từ `style` và `occasion`, rồi chuyển xuống
    `hybrid_search` giống như một truy vấn tìm kiếm thông thường.

    Tham số:
        style: Phong cách mục tiêu, ví dụ casual hoặc formal.
        occasion: Dịp sử dụng, ví dụ office hoặc wedding.
        gender: Bộ lọc giới tính tùy chọn.
        top_k: Số sản phẩm tối đa mỗi lượt tìm.

    Trả về:
        Danh sách product dict.
    """
    from search.search_engine import search as hybrid_search

    parts = []
    if occasion:
        parts.append(occasion)
    if style:
        parts.append(style)
    if not parts:
        parts = ["fashion outfit"]

    query = " ".join(parts) + " outfit"

    filters: dict[str, str] = {}
    if gender and gender not in ("", "unisex"):
        filters["gender"] = gender

    try:
        results = hybrid_search(query, top_k=top_k, use_query_expansion=False, filters=filters)
        return [
            {
                "image_id": r.image_id,
                "image_path": r.image_path,
                "label": r.label,
                "color": r.color,
                "caption": r.caption,
                "score": round(r.score, 4),
            }
            for r in results
        ]
    except Exception as exc:
        logger.error("run_recommend_tool failed: %s", exc)
        return []
